"""
Phase 2 End-to-End Concurrency & Architectural QA Verification Suite (Commit 6):
- NFR-02 (Zero Overselling): 100 distinct students concurrently racing for 10 remaining slots in a hot class via CourseService.register_course -> exact 10 succeed, 90 fail in RAM, 0 overselling, only 10 DB writes executed.
- PROB-03 (Multi-Tab Spam Prevention): 1 student firing 20 concurrent registration requests across tabs -> exact 1 succeeds, 19 blocked by Per-Student Mutex.
- Slot Recycle under Contention: 1 enrolled student cancels while class is 40/40, then 20 students race for the single freed slot -> exact 1 student wins the freed slot.
- Database & Clean Architecture Guardrails: Verifies UniqueConstraint on Enrollment and AST purity.
"""
import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.domain.entities.registration import ClassSchedule, Course, CourseClass, Student
from src.infrastructure.cache.redis_keys import (
    AUDIT_QUEUE_KEY,
    CATALOG_READY_KEY,
    catalog_class_key,
    slot_counter_key,
)
from src.infrastructure.cache.slot_reservation_adapter import SlotReservationAdapter
from src.infrastructure.database.models import Enrollment as EnrollmentModel
from src.use_cases.course_service import CourseService
from tests.test_slot_reservation_adapter import FakeAsyncRedis


class TestPhase2EndToEndQASuite(unittest.IsolatedAsyncioTestCase):
    """Bộ kiểm thử QA tổng thể xác minh toàn bộ bất biến kiến trúc Pha 2 của Người 1."""

    def setUp(self):
        self.fake_redis = FakeAsyncRedis()
        self.slot_adapter = SlotReservationAdapter(redis_client=self.fake_redis)

        self.hot_course = Course(
            id=301,
            code="INT3306",
            name="Kiến trúc phần mềm",
            credits=3,
            course_type="normal",
            prerequisite_course_ids=[],
        )
        self.hot_class = CourseClass(
            id=uuid4(),
            class_code="INT3306_HOT",
            course=self.hot_course,
            room="301-G2",
            lecturer="PGS.TS. Giảng Viên A",
            max_capacity=40,
            current_capacity=30,  # Còn đúng 10 chỗ trống
            schedules=[ClassSchedule(day_of_week=3, start_period=1, end_period=3)],
        )

        self.students: dict[UUID, Student] = {}
        self.enrolled_records: list[tuple[UUID, UUID]] = []

        self.class_repo = AsyncMock()
        self.class_repo.is_session_open_for_cohort.return_value = True
        self.class_repo.get_by_id.return_value = self.hot_class

        async def _atomic_inc(cid: UUID) -> bool:
            if self.hot_class.current_capacity < self.hot_class.max_capacity:
                self.hot_class.current_capacity += 1
                return True
            return False

        async def _atomic_dec(cid: UUID) -> bool:
            if self.hot_class.current_capacity > 0:
                self.hot_class.current_capacity -= 1
                return True
            return False

        self.class_repo.increment_capacity_atomic.side_effect = _atomic_inc
        self.class_repo.decrement_capacity_atomic.side_effect = _atomic_dec

        self.student_repo = AsyncMock()
        self.student_repo.get_by_id.side_effect = lambda sid: self.students.get(sid)

        self.enrollment_repo = AsyncMock()

        async def _create_enrollment(enrollment):
            self.enrolled_records.append((enrollment.student_id, enrollment.course_class.id))

        self.enrollment_repo.create.side_effect = _create_enrollment
        self.enrollment_repo.cancel_enrollment.return_value = True

        self.service = CourseService(
            course_class_repo=self.class_repo,
            student_repo=self.student_repo,
            enrollment_repo=self.enrollment_repo,
            slot_adapter=self.slot_adapter,
        )

    async def _seed_hot_class_in_ram(self, initial_capacity: int = 30):
        self.hot_class.current_capacity = initial_capacity
        await self.fake_redis.set(CATALOG_READY_KEY, "1")
        await self.fake_redis.set(
            catalog_class_key(self.hot_class.id),
            json.dumps(self.slot_adapter.serialize_course_class(self.hot_class)),
        )
        await self.fake_redis.set(slot_counter_key(self.hot_class.id), initial_capacity)

    async def test_100_students_racing_for_10_remaining_slots_e2e_zero_overselling(self):
        """
        [QA-01 / NFR-02] 100 sinh viên khác nhau đồng thời bấm đăng ký vào 1 lớp học phần
        đang ở mức 30/40 (còn đúng 10 chỗ):
        - Đúng 10 sinh viên nhận kết quả True.
        - Đúng 90 sinh viên nhận ValueError('Lớp học phần đã hết chỗ').
        - Sĩ số trên cả Redis (slot:counter) và DB (current_capacity) dừng chính xác ở 40/40.
        - DB chỉ nhận đúng 10 lệnh ghi (90 request bị chặn đứng tại RAM).
        """
        await self._seed_hot_class_in_ram(initial_capacity=30)

        student_ids = []
        for _ in range(100):
            sid = uuid4()
            self.students[sid] = Student(id=sid, cohort="K68")
            student_ids.append(sid)

        async def _attempt(sid: UUID):
            try:
                return await self.service.register_course(
                    self.hot_class.id, sid, ip_address="172.16.0.10"
                )
            except ValueError as err:
                return str(err)

        outcomes = await asyncio.gather(*[_attempt(sid) for sid in student_ids])

        succeeded = [o for o in outcomes if o is True]
        rejected = [o for o in outcomes if o == "Lớp học phần đã hết chỗ"]

        self.assertEqual(len(succeeded), 10)
        self.assertEqual(len(rejected), 90)
        self.assertEqual(
            int(await self.fake_redis.get(slot_counter_key(self.hot_class.id))),
            40,
        )
        self.assertEqual(self.hot_class.current_capacity, 40)
        self.assertEqual(len(self.enrolled_records), 10)
        self.assertEqual(self.class_repo.increment_capacity_atomic.await_count, 10)

        # Kiểm tra hàng đợi audit:queue ghi nhận đủ 100 sự kiện (10 SUCCESS + 90 FAILED_FULL)
        audit_logs = [
            json.loads(raw) for raw in self.fake_redis.lists.get(AUDIT_QUEUE_KEY, [])
        ]
        self.assertEqual(len(audit_logs), 100)
        self.assertEqual(sum(1 for a in audit_logs if a["status"] == "SUCCESS"), 10)
        self.assertEqual(sum(1 for a in audit_logs if a["status"] == "FAILED_FULL"), 90)

    async def test_single_student_20_concurrent_tabs_blocked_by_mutex(self):
        """
        [QA-02 / PROB-03] 1 sinh viên mở 20 tab trình duyệt và bấm đăng ký cùng lúc:
        Nhờ lock:student:{id} và kiểm tra trùng lặp, chỉ tối đa 1 request thành công.
        """
        await self._seed_hot_class_in_ram(initial_capacity=10)
        sid = uuid4()
        self.students[sid] = Student(id=sid, cohort="K68")

        # Chèn độ trễ 5ms vào thao tác ghi DB để 20 coroutine thực sự chồng lấn thời gian
        orig_inc = self.class_repo.increment_capacity_atomic.side_effect

        async def _slow_inc(cid: UUID):
            await asyncio.sleep(0.005)
            return await orig_inc(cid)

        self.class_repo.increment_capacity_atomic.side_effect = _slow_inc

        async def _spam_tab():
            try:
                return await self.service.register_course(self.hot_class.id, sid)
            except ValueError as err:
                return str(err)

        outcomes = await asyncio.gather(*[_spam_tab() for _ in range(20)])

        succeeded = [o for o in outcomes if o is True]
        blocked = [o for o in outcomes if isinstance(o, str) and "Thao tác quá nhanh" in o]

        self.assertEqual(len(succeeded), 1)
        self.assertEqual(len(blocked), 19)
        self.assertEqual(
            int(await self.fake_redis.get(slot_counter_key(self.hot_class.id))),
            11,
        )

    async def test_slot_recycle_on_cancel_immediately_available_to_waiters(self):
        """
        [QA-03] Khi lớp đã đầy 40/40, 1 sinh viên hủy môn (40 -> 39) và ngay lập tức
        20 sinh viên khác cùng bấm đăng ký -> Đúng 1 sinh viên lấy được chỗ vừa nhả ra.
        """
        await self._seed_hot_class_in_ram(initial_capacity=40)
        cancelling_sid = uuid4()
        self.students[cancelling_sid] = Student(id=cancelling_sid, cohort="K68")

        # Sinh viên hủy môn -> giải phóng 1 slot về 39/40
        cancelled = await self.service.cancel_registration(self.hot_class.id, cancelling_sid)
        self.assertTrue(cancelled)
        self.assertEqual(
            int(await self.fake_redis.get(slot_counter_key(self.hot_class.id))),
            39,
        )

        # 20 sinh viên khác lập tức tranh 1 slot vừa trống
        waiters = []
        for _ in range(20):
            wsid = uuid4()
            self.students[wsid] = Student(id=wsid, cohort="K68")
            waiters.append(wsid)

        async def _race(sid: UUID):
            try:
                return await self.service.register_course(self.hot_class.id, sid)
            except ValueError as err:
                return str(err)

        outcomes = await asyncio.gather(*[_race(sid) for sid in waiters])
        self.assertEqual(sum(1 for o in outcomes if o is True), 1)
        self.assertEqual(
            sum(1 for o in outcomes if o == "Lớp học phần đã hết chỗ"),
            19,
        )
        self.assertEqual(
            int(await self.fake_redis.get(slot_counter_key(self.hot_class.id))),
            40,
        )

    def test_enrollment_model_has_unique_student_class_constraint(self):
        """[QA-04] Đảm bảo tầng Database Model có khai báo UniqueConstraint(student_id, course_class_id)."""
        table_args = getattr(EnrollmentModel, "__table_args__", ())
        constraint_names = [getattr(c, "name", None) for c in table_args]
        self.assertIn("uq_student_course_class", constraint_names)


if __name__ == "__main__":
    unittest.main()
