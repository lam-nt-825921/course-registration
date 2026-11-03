from typing import Optional
from uuid import UUID
import uuid

from src.domain.entities.registration import CourseClass, Enrollment, Student
from src.domain.ports import (
    ICourseClassRepository,
    IEnrollmentRepository,
    ISlotReservationPort,
    IStudentRepository,
)


class CourseService:
    """
    Use Case trung tâm xử lý nghiệp vụ Đăng ký học phần và Hủy học phần (Pha 2):
    - Tách biệt 100% khỏi SQLAlchemy/Redis trực tiếp (Clean Architecture - NFR-03).
    - Hỗ trợ Cơ chế Giữ chỗ 2 Pha (Two-Phase Slot Reservation - ADR-01):
      + Pha 1 (Hot State / RAM): Khóa chống gửi trùng theo sinh viên (Per-Student Mutex),
        kiểm tra điều kiện học vụ (BR1..BR6) và giữ chỗ nguyên tử bằng Lua Script trong < 1ms.
      + Pha 2 (Cold State / DB): Ghi nhận bền vững bằng Conditional Atomic Update, tự động
        chạy Giao dịch bù trừ (Compensating Transaction) hoàn trả slot nếu DB gặp lỗi.
      + Đẩy nhật ký kiểm toán bất đồng bộ (Async Audit Queue - NFR-04).
    """

    def __init__(
        self,
        course_class_repo: ICourseClassRepository,
        student_repo: IStudentRepository,
        enrollment_repo: IEnrollmentRepository,
        slot_adapter: Optional[ISlotReservationPort] = None,
    ):
        self.course_class_repo = course_class_repo
        self.student_repo = student_repo
        self.enrollment_repo = enrollment_repo
        self.slot_adapter = slot_adapter

    async def get_all_courses(
        self,
        student_id: UUID,
        keyword: Optional[str] = None,
        can_register: Optional[bool] = None,
        day_of_week: Optional[int] = None,
        course_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        return await self.course_class_repo.get_all(
            student_id=student_id,
            keyword=keyword,
            can_register=can_register,
            day_of_week=day_of_week,
            course_type=course_type,
            page=page,
            size=size,
        )

    async def _check_session(self, student: Optional[Student]) -> bool:
        if not student:
            return False
        if hasattr(self.course_class_repo, "is_session_open_for_cohort"):
            return await self.course_class_repo.is_session_open_for_cohort(student.cohort)
        return True

    async def _load_student(self, student_id: UUID) -> Optional[Student]:
        if self.slot_adapter is not None:
            return await self.slot_adapter.get_or_load_student(student_id, self.student_repo)
        return await self.student_repo.get_by_id(student_id)

    async def _load_course_class(self, class_id: UUID) -> Optional[CourseClass]:
        if self.slot_adapter is not None:
            return await self.slot_adapter.get_or_load_course_class(class_id, self.course_class_repo)
        if hasattr(self.course_class_repo, "get_by_id"):
            return await self.course_class_repo.get_by_id(class_id)
        return await self.course_class_repo.get_by_id_for_update(class_id)

    async def register_course(
        self,
        class_id: UUID,
        student_id: UUID,
        ip_address: Optional[str] = None,
    ) -> bool:
        # Bước 1: Khóa phân tán ngắn hạn theo sinh viên (Per-Student Mutex - PROB-03)
        if self.slot_adapter is not None:
            locked = await self.slot_adapter.acquire_student_lock(student_id, ttl=5)
            if not locked:
                raise ValueError("Thao tác quá nhanh, yêu cầu đăng ký trước đó đang được xử lý")

        try:
            # Bước 2: Đọc trạng thái học tập & kiểm tra quy tắc nghiệp vụ trên RAM (BR1..BR6)
            student = await self._load_student(student_id)
            if not student:
                raise ValueError("Không tìm thấy sinh viên")

            if not await self._check_session(student):
                raise ValueError("Ngoài thời gian đăng ký của bạn")

            course_class = await self._load_course_class(class_id)
            if not course_class:
                raise ValueError("Không tìm thấy Lớp học phần")

            # BR-06: Chặn đăng ký trùng lớp học phần đang active
            if any(
                e.course_class.id == class_id and e.status == "enrolled"
                for e in student.enrollments
            ):
                raise ValueError("Sinh viên đã đăng ký lớp học phần này rồi")

            course = course_class.course

            # BR-01: Trần tối đa 25 tín chỉ (không tính GDTC)
            if student.get_total_registered_credits() + course.credits > 25:
                raise ValueError("Vượt quá giới hạn tín chỉ tối đa")

            # BR-02: Tối đa 1 môn Giáo dục thể chất mỗi học kỳ
            if (
                course.course_type == "physical_education"
                and student.count_physical_education_courses() >= 1
            ):
                raise ValueError("Chỉ được đăng ký tối đa 1 môn Giáo dục thể chất")

            # BR-04: Điều kiện môn tiên quyết
            for prereq_id in course.prerequisite_course_ids:
                if not student.has_passed_course(prereq_id):
                    raise ValueError("Chưa đạt môn tiên quyết")

            # BR-05: Xung đột thời khóa biểu
            if student.has_schedule_conflict(course_class.schedules):
                raise ValueError("Trùng lịch học")

            # Bước 3: Pha 1 (Hot State) - Giữ chỗ nguyên tử bằng Lua Script trên Redis
            slot_reserved_in_ram = False
            if self.slot_adapter is not None:
                slot_reserved_in_ram = await self.slot_adapter.reserve_slot(
                    class_id=class_id,
                    max_capacity=course_class.max_capacity,
                    course_class_repo=self.course_class_repo,
                    initial_capacity=course_class.current_capacity,
                )
                if not slot_reserved_in_ram:
                    await self.slot_adapter.push_audit_log(
                        student_id=student_id,
                        action="ENROLLED",
                        class_code=course_class.class_code,
                        status="FAILED_FULL",
                        ip_address=ip_address,
                    )
                    raise ValueError("Lớp học phần đã hết chỗ")
            else:
                if not course_class.can_register():
                    raise ValueError("Lớp học phần đã hết chỗ")

            # Bước 4: Pha 2 (Cold State) - Ghi nhận bền vững xuống DB & Giao dịch bù trừ (ADR-01)
            try:
                if hasattr(self.course_class_repo, "increment_capacity_atomic"):
                    updated = await self.course_class_repo.increment_capacity_atomic(class_id)
                    if not updated:
                        raise ValueError("Lớp học phần đã hết chỗ")
                    course_class.current_capacity += 1
                else:
                    course_class.current_capacity += 1
                    await self.course_class_repo.save(course_class)

                enrollment = Enrollment(
                    id=uuid.uuid4(),
                    student_id=student_id,
                    course_class=course_class,
                    status="enrolled",
                )
                await self.enrollment_repo.create(enrollment)
            except Exception:
                if self.slot_adapter is not None and slot_reserved_in_ram:
                    await self.slot_adapter.release_slot(class_id)
                raise

            # Bước 5: Làm mới trạng thái sinh viên trên RAM & Đẩy Audit Log bất đồng bộ (NFR-04)
            if self.slot_adapter is not None:
                await self.slot_adapter.invalidate_student_state(student_id)
                await self.slot_adapter.push_audit_log(
                    student_id=student_id,
                    action="ENROLLED",
                    class_code=course_class.class_code,
                    status="SUCCESS",
                    ip_address=ip_address,
                    details={
                        "course_class_id": str(class_id),
                        "credits": course.credits,
                    },
                )
            elif hasattr(self.course_class_repo, "record_audit_log"):
                await self.course_class_repo.record_audit_log(
                    student_id=student_id,
                    course_class_id=class_id,
                    action="ENROLLED",
                    ip_address=ip_address,
                )

            return True
        finally:
            if self.slot_adapter is not None:
                await self.slot_adapter.release_student_lock(student_id)

    async def get_my_schedule(self, student_id: UUID) -> list:
        student = await self._load_student(student_id)
        if not student:
            return []
        return [e.course_class for e in student.enrollments if e.status == "enrolled"]

    async def cancel_registration(
        self,
        class_id: UUID,
        student_id: UUID,
        ip_address: Optional[str] = None,
    ) -> bool:
        if self.slot_adapter is not None:
            locked = await self.slot_adapter.acquire_student_lock(student_id, ttl=5)
            if not locked:
                raise ValueError("Thao tác quá nhanh, yêu cầu trước đó đang được xử lý")

        try:
            student = await self._load_student(student_id)
            if not await self._check_session(student):
                raise ValueError("Ngoài thời gian đăng ký của bạn")

            course_class = await self._load_course_class(class_id)
            if not course_class:
                raise ValueError("Không tìm thấy Lớp học phần")

            success = await self.enrollment_repo.cancel_enrollment(student_id, class_id)
            if not success:
                raise ValueError("Bạn chưa đăng ký lớp này")

            if hasattr(self.course_class_repo, "decrement_capacity_atomic"):
                await self.course_class_repo.decrement_capacity_atomic(class_id)
                if course_class.current_capacity > 0:
                    course_class.current_capacity -= 1
            else:
                course_class.current_capacity -= 1
                await self.course_class_repo.save(course_class)

            if self.slot_adapter is not None:
                await self.slot_adapter.release_slot(class_id)
                await self.slot_adapter.invalidate_student_state(student_id)
                await self.slot_adapter.push_audit_log(
                    student_id=student_id,
                    action="CANCELLED",
                    class_code=course_class.class_code,
                    status="SUCCESS",
                    ip_address=ip_address,
                    details={"course_class_id": str(class_id)},
                )
            elif hasattr(self.course_class_repo, "record_audit_log"):
                await self.course_class_repo.record_audit_log(
                    student_id=student_id,
                    course_class_id=class_id,
                    action="CANCELLED",
                    ip_address=ip_address,
                )

            return True
        finally:
            if self.slot_adapter is not None:
                await self.slot_adapter.release_student_lock(student_id)

    async def get_enrollment_history(self, student_id: UUID) -> list:
        student = await self.student_repo.get_by_id(student_id)
        if not student:
            return []

        classes = []
        for e in student.enrollments:
            if e.status == "enrolled":
                classes.append(
                    {
                        "id": e.course_class.id,
                        "class_code": getattr(e.course_class, "class_code", ""),
                        "course_code": e.course_class.course.code,
                        "credits": e.course_class.course.credits,
                        "course_type": e.course_class.course.course_type,
                        "max_capacity": e.course_class.max_capacity,
                        "current_capacity": e.course_class.current_capacity,
                        "schedules": [
                            {
                                "day_of_week": s.day_of_week,
                                "start_period": s.start_period,
                                "end_period": s.end_period,
                            }
                            for s in e.course_class.schedules
                        ],
                    }
                )
        return [{"semester_code": "20241", "course_classes": classes}]
