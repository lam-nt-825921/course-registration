from uuid import UUID
from typing import List, Optional
from src.domain.entities.registration import CourseClass, Enrollment
import uuid

class CourseService:
    def __init__(self, course_class_repo, student_repo, enrollment_repo):
        self.course_class_repo = course_class_repo
        self.student_repo = student_repo
        self.enrollment_repo = enrollment_repo

    async def get_all_courses(self, keyword: Optional[str] = None, can_register: Optional[bool] = None, day_of_week: Optional[int] = None, course_type: Optional[str] = None) -> list:
        # Pass filters to repository
        return await self.course_class_repo.get_all(keyword=keyword, can_register=can_register, day_of_week=day_of_week, course_type=course_type)

    async def register_course(self, class_id: UUID, student_id: UUID) -> bool:
        student = await self.student_repo.get_by_id(student_id)
        if not student:
            raise ValueError("Không tìm thấy sinh viên")

        course_class = await self.course_class_repo.get_by_id_for_update(class_id)
        if not course_class:
            raise ValueError("Không tìm thấy Lớp học phần")
        
        if not course_class.can_register():
            raise ValueError("Lớp học phần đã hết chỗ")
            
        course = course_class.course
        
        if student.get_total_registered_credits() + course.credits > 25:
            raise ValueError("Vượt quá giới hạn tín chỉ tối đa")
            
        if course.course_type == "physical_education" and student.count_physical_education_courses() >= 1:
            raise ValueError("Chỉ được đăng ký tối đa 1 môn Giáo dục thể chất")

        for prereq_id in course.prerequisite_course_ids:
            if not student.has_passed_course(prereq_id):
                raise ValueError("Chưa đạt môn tiên quyết")

        if student.has_schedule_conflict(course_class.schedules):
            raise ValueError("Trùng lịch học")

        course_class.current_capacity += 1
        await self.course_class_repo.save(course_class)
        
        enrollment = Enrollment(id=uuid.uuid4(), student_id=student_id, course_class=course_class, status="enrolled")
        await self.enrollment_repo.create(enrollment)
        
        return True

    async def get_my_schedule(self, student_id: UUID) -> list:
        student = await self.student_repo.get_by_id(student_id)
        if not student:
            return []
        return [e.course_class for e in student.enrollments if e.status == "enrolled"]

    async def cancel_registration(self, class_id: UUID, student_id: UUID) -> bool:
        # Khóa class để trả slot
        course_class = await self.course_class_repo.get_by_id_for_update(class_id)
        if not course_class:
            raise ValueError("Không tìm thấy Lớp học phần")
            
        success = await self.enrollment_repo.cancel_enrollment(student_id, class_id)
        if not success:
            raise ValueError("Bạn chưa đăng ký lớp này")
            
        # Trả slot
        course_class.current_capacity -= 1
        await self.course_class_repo.save(course_class)
        return True
        
    async def get_enrollment_history(self, student_id: UUID) -> list:
        student = await self.student_repo.get_by_id(student_id)
        if not student:
            return []
        
        # Real mapping for E2E
        classes = []
        for e in student.enrollments:
            # only show enrolled? For history we can show all, but let's just dump
            if e.status == 'enrolled':
                classes.append({
                    "id": e.course_class.id,
                    "class_code": getattr(e.course_class, "class_code", ""),
                    "course_code": e.course_class.course.code,
                    "credits": e.course_class.course.credits,
                    "course_type": e.course_class.course.course_type,
                    "max_capacity": e.course_class.max_capacity,
                    "current_capacity": e.course_class.current_capacity,
                    "schedules": [{"day_of_week": s.day_of_week, "start_period": s.start_period, "end_period": s.end_period} for s in e.course_class.schedules]
                })
        return [{"semester_code": "20241", "course_classes": classes}]
