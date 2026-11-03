"""
Unit & Integration Tests for Commit 5:
- Two-Phase Slot Reservation (Hot State RAM Lua Gate + Cold State DB Persistence).
- Compensating Transaction (ADR-01): Rollback Redis slot counter when DB write fails.
- All Business Rules (BR-01..BR-06) validated in memory before touching DB.
- Per-Student Distributed Mutex blocking multi-tab spam.
- Course Cancellation releasing slot back to Redis RAM and pushing to audit:queue.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.domain.entities.registration import (
    AcademicTranscript,
    ClassSchedule,
    Course,
    CourseClass,
    Enrollment,
    Student,
)
from src.infrastructure.cache.redis_keys import (
    AUDIT_QUEUE_KEY,
    CATALOG_READY_KEY,
    slot_counter_key,
    student_lock_key,
)
from src.infrastructure.cache.slot_reservation_adapter import SlotReservationAdapter
from src.use_cases.course_service import CourseService
from tests.test_slot_reservation_adapter import FakeAsyncRedis


class TestCourseServicePhase2(unittest.IsolatedAsyncioTestCase):
    """Kiểm thử toàn diện luồng ghi 2 pha (Two-Phase Slot Reservation) trong CourseService."""

    def setUp(self):
        self.fake_redis = FakeAsyncRedis()
        self.slot_adapter = SlotReservationAdapter(redis_client=self.fake_redis)

        self.class_repo = AsyncMock()
        self.class_repo.is_session_open_for_cohort.return_value = True
        self.class_repo.increment_capacity_atomic.return_value = True
        self.class_repo.decrement_capacity_atomic.return_value = True

        self.student_repo = AsyncMock()
        self.enrollment_repo = AsyncMock()
        self.enrollment_repo.cancel_enrollment.return_value = True

        self.service = CourseService(
            course_class_repo=self.class_repo,
            student_repo=self.student_repo,
            enrollment_repo=self.enrollment_repo,
            slot_adapter=self.slot_adapter,
        )

    def _make_class(
        self,
        credits: int = 3,
        course_type: str = "normal",
        max_capacity: int = 40,
        current_capacity: int = 10,
        prereqs: list[int] | None = None,
        schedules: list[ClassSchedule] | None = None,
    ) -> CourseClass:
        course = Course(
            id=101,
            code="INT3306",
            name="Kiến trúc phần mềm",
            credits=credits,
            course_type=course_type,
            prerequisite_course_ids=prereqs or [],
        )
        return CourseClass(
            id=uuid4(),
            class_code="INT3306_1",
            course=course,
            room="301-G2",
            lecturer="TS. Nguyễn Văn A",
            max_capacity=max_capacity,
            current_capacity=current_capacity,
            schedules=schedules or [ClassSchedule(day_of_week=2, start_period=1, end_period=3)],
        )

    async def test_two_phase_register_course_success_and_audit_push(self):
        """
        Kiểm thử đăng ký thành công qua 2 pha:
        1. Giữ chỗ trên RAM (slot:counter tăng từ 10 -> 11).
        2. Ghi DB qua increment_capacity_atomic + enrollment_repo.create.
        3. Đẩy log ENROLLED (SUCCESS) kèm IP vào audit:queue.
        4. Giải phóng khóa lock:student:{id} sau khi hoàn tất.
        """
        student_id = uuid4()
        student = Student(id=student_id, cohort="K68")
        cc = self._make_class(current_capacity=10, max_capacity=40)

        self.student_repo.get_by_id.return_value = student
        self.class_repo.get_by_id.return_value = cc
        await self.fake_redis.set(CATALOG_READY_KEY, "1")
        await self.fake_redis.set(slot_counter_key(cc.id), 10)

        ok = await self.service.register_course(cc.id, student_id, ip_address="10.0.0.15")

        self.assertTrue(ok)
        self.assertEqual(int(await self.fake_redis.get(slot_counter_key(cc.id))), 11)
        self.class_repo.increment_capacity_atomic.assert_awaited_once_with(cc.id)
        self.enrollment_repo.create.assert_awaited_once()
        self.assertEqual(await self.fake_redis.exists(student_lock_key(student_id)), 0)

        audit_items = self.fake_redis.lists.get(AUDIT_QUEUE_KEY, [])
        self.assertEqual(len(audit_items), 1)
        audit = json.loads(audit_items[0])
        self.assertEqual(audit["action"], "ENROLLED")
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertEqual(audit["ip_address"], "10.0.0.15")

    async def test_compensating_transaction_rolls_back_redis_slot_when_db_fails(self):
        """
        Kiểm thử Giao dịch bù trừ (Compensating Transaction - ADR-01):
        Khi Pha 1 (Redis Lua) đã giữ được slot thứ 40 (39 -> 40), nhưng Pha 2 (DB create)
        ném ngoại lệ -> CourseService phải lập tức gọi release_slot() trả bộ đếm Redis về 39!
        """
        student_id = uuid4()
        student = Student(id=student_id, cohort="K68")
        cc = self._make_class(current_capacity=39, max_capacity=40)

        self.student_repo.get_by_id.return_value = student
        self.class_repo.get_by_id.return_value = cc
        self.enrollment_repo.create.side_effect = RuntimeError("Database connection lost")

        await self.fake_redis.set(CATALOG_READY_KEY, "1")
        await self.fake_redis.set(slot_counter_key(cc.id), 39)

        with self.assertRaises(RuntimeError):
            await self.service.register_course(cc.id, student_id)

        # Bộ đếm trên Redis phải được hoàn trả về đúng 39 (không bị kẹt slot ảo ở 40)
        self.assertEqual(int(await self.fake_redis.get(slot_counter_key(cc.id))), 39)
        # Lock sinh viên cũng phải được giải phóng trong finally
        self.assertEqual(await self.fake_redis.exists(student_lock_key(student_id)), 0)

    async def test_full_class_rejected_at_ram_gate_without_touching_db(self):
        """
        Kiểm thử BR-03 tại RAM Slot Gate:
        Khi slot:counter == max_capacity (40/40), yêu cầu bị chặn ngay tại Redis Lua Script,
        TUYỆT ĐỐI không gọi xuống DB (increment_capacity_atomic & create = 0 lần gọi).
        """
        student_id = uuid4()
        student = Student(id=student_id, cohort="K68")
        cc = self._make_class(current_capacity=40, max_capacity=40)

        self.student_repo.get_by_id.return_value = student
        self.class_repo.get_by_id.return_value = cc
        await self.fake_redis.set(CATALOG_READY_KEY, "1")
        await self.fake_redis.set(slot_counter_key(cc.id), 40)

        with self.assertRaises(ValueError) as ctx:
            await self.service.register_course(cc.id, student_id)

        self.assertIn("hết chỗ", str(ctx.exception))
        self.class_repo.increment_capacity_atomic.assert_not_awaited()
        self.enrollment_repo.create.assert_not_awaited()

    async def test_business_rules_br1_br2_br4_br5_br6_enforced_in_memory(self):
        """Kiểm thử toàn bộ quy tắc học vụ BR-01, BR-02, BR-04, BR-05, BR-06."""
        student_id = uuid4()
        existing_cc = self._make_class(
            credits=24,
            course_type="physical_education",
            schedules=[ClassSchedule(day_of_week=2, start_period=1, end_period=3)],
        )
        existing_enrollment = Enrollment(
            id=uuid4(),
            student_id=student_id,
            course_class=existing_cc,
            status="enrolled",
        )
        student = Student(
            id=student_id,
            cohort="K68",
            enrollments=[existing_enrollment],
            transcripts=[AcademicTranscript(course_id=1, status="failed")],
        )
        self.student_repo.get_by_id.return_value = student

        # BR-06: Đăng ký trùng chính lớp đã đăng ký
        self.class_repo.get_by_id.return_value = existing_cc
        with self.assertRaises(ValueError) as ctx:
            await self.service.register_course(existing_cc.id, student_id)
        self.assertIn("đã đăng ký", str(ctx.exception))

        # BR-02: Đăng ký môn GDTC thứ 2 trong kỳ
        await self.slot_adapter.invalidate_student_state(student_id)
        pe_cc_2 = self._make_class(
            credits=1,
            course_type="physical_education",
            schedules=[ClassSchedule(day_of_week=4, start_period=1, end_period=2)],
        )
        self.class_repo.get_by_id.return_value = pe_cc_2
        with self.assertRaises(ValueError) as ctx:
            await self.service.register_course(pe_cc_2.id, student_id)
        self.assertIn("Giáo dục thể chất", str(ctx.exception))

        # BR-04: Chưa đạt môn tiên quyết (course_id=1 mới chỉ failed, chưa passed)
        prereq_cc = self._make_class(
            credits=2,
            course_type="normal",
            prereqs=[1],
            schedules=[ClassSchedule(day_of_week=5, start_period=1, end_period=2)],
        )
        self.class_repo.get_by_id.return_value = prereq_cc
        with self.assertRaises(ValueError) as ctx:
            await self.service.register_course(prereq_cc.id, student_id)
        self.assertIn("tiên quyết", str(ctx.exception))

        # BR-05: Trùng lịch học Thứ 2 tiết 2-4 (xung đột với tiết 1-3)
        conflict_cc = self._make_class(
            credits=2,
            course_type="normal",
            schedules=[ClassSchedule(day_of_week=2, start_period=2, end_period=4)],
        )
        self.class_repo.get_by_id.return_value = conflict_cc
        with self.assertRaises(ValueError) as ctx:
            await self.service.register_course(conflict_cc.id, student_id)
        self.assertIn("Trùng lịch học", str(ctx.exception))

    async def test_cancel_registration_releases_redis_slot_and_logs_audit(self):
        """
        Kiểm thử luồng Hủy học phần (cancel_registration):
        Giảm sĩ số dưới DB, trả lại 1 slot trên Redis (40 -> 39) để sinh viên khác
        đăng ký được ngay, và đẩy log CANCELLED vào audit:queue.
        """
        student_id = uuid4()
        student = Student(id=student_id, cohort="K68")
        cc = self._make_class(current_capacity=40, max_capacity=40)

        self.student_repo.get_by_id.return_value = student
        self.class_repo.get_by_id.return_value = cc
        await self.fake_redis.set(CATALOG_READY_KEY, "1")
        await self.fake_redis.set(slot_counter_key(cc.id), 40)

        ok = await self.service.cancel_registration(cc.id, student_id, ip_address="10.0.0.15")

        self.assertTrue(ok)
        self.assertEqual(int(await self.fake_redis.get(slot_counter_key(cc.id))), 39)
        self.enrollment_repo.cancel_enrollment.assert_awaited_once_with(student_id, cc.id)
        self.class_repo.decrement_capacity_atomic.assert_awaited_once_with(cc.id)

        audit_items = self.fake_redis.lists.get(AUDIT_QUEUE_KEY, [])
        self.assertEqual(len(audit_items), 1)
        audit = json.loads(audit_items[0])
        self.assertEqual(audit["action"], "CANCELLED")
        self.assertEqual(audit["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
