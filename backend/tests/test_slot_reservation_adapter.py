"""
Unit & Concurrency Verification Tests for Commit 4:
- Atomic Slot Reservation (LUA_RESERVE_SLOT): 100 concurrent requests competing for 5 remaining slots -> exact 5 succeed, 95 rejected, 0 overselling.
- Compensating Transaction (LUA_RELEASE_SLOT): Decrements slot counter atomically and never drops below 0.
- Per-Student Distributed Mutex (lock:student:{id}): Blocks concurrent multi-tab requests from the same student.
- 4-Step RAM Crash Recovery (ADR-03): Singleflight lock:rebuild_ram rebuilds catalog:class:* and slot:counter:* from PostgreSQL when catalog:ready is missing, while blocking stampeding followers.
"""
import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.domain.entities.registration import ClassSchedule, Course, CourseClass
from src.infrastructure.cache.redis_keys import (
    AUDIT_QUEUE_KEY,
    CATALOG_READY_KEY,
    REBUILD_LOCK_KEY,
    catalog_class_key,
    slot_counter_key,
)
from src.infrastructure.cache.slot_reservation_adapter import (
    LUA_RELEASE_SLOT,
    LUA_RESERVE_SLOT,
    SlotReservationAdapter,
    SystemRebuildInProgressError,
)


class FakeAsyncRedisPipeline:
    """In-memory pipeline mô phỏng thực thi nguyên tử (MULTI/EXEC) của Redis."""

    def __init__(self, store: dict, lists: dict):
        self._store = store
        self._lists = lists
        self._ops = []

    def set(self, key: str, value: str | int):
        self._ops.append(("set", key, str(value)))
        return self

    async def execute(self):
        results = []
        for op, key, val in self._ops:
            if op == "set":
                self._store[key] = val
                results.append(True)
        self._ops.clear()
        return results


class FakeAsyncRedis:
    """
    In-memory Single-Threaded Redis Emulator thực thi chính xác ngữ nghĩa nguyên tử
    của LUA_RESERVE_SLOT, LUA_RELEASE_SLOT, SET NX EX, Pipeline và List Queue.
    """

    def __init__(self):
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str | int, nx: bool = False, ex: int | None = None):
        if nx and key in self.store:
            return False
        self.store[key] = str(value)
        return True

    async def setnx(self, key: str, value: str | int):
        if key in self.store:
            return False
        self.store[key] = str(value)
        return True

    async def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    async def lpush(self, key: str, value: str) -> int:
        lst = self.lists.setdefault(key, [])
        lst.insert(0, value)
        return len(lst)

    def pipeline(self, transaction: bool = True):
        return FakeAsyncRedisPipeline(self.store, self.lists)

    async def eval(self, script: str, numkeys: int, *keys_and_args):
        key = keys_and_args[0]
        if script == LUA_RESERVE_SLOT:
            max_cap = int(keys_and_args[1])
            if key not in self.store:
                return -1
            current = int(self.store[key])
            if current < max_cap:
                self.store[key] = str(current + 1)
                return 1
            return 0
        elif script == LUA_RELEASE_SLOT:
            if key not in self.store:
                return 0
            current = int(self.store[key])
            if current > 0:
                self.store[key] = str(current - 1)
                return current - 1
            return 0
        raise NotImplementedError(f"Unsupported Lua script in test: {script}")


class TestSlotReservationAdapter(unittest.IsolatedAsyncioTestCase):
    """Kiểm thử toàn diện Commit 4: Atomic Slot Gate, Per-Student Mutex & 4-Step Crash Recovery."""

    def setUp(self):
        self.fake_redis = FakeAsyncRedis()
        self.adapter = SlotReservationAdapter(redis_client=self.fake_redis)

    async def test_100_concurrent_requests_for_5_remaining_slots_zero_overselling(self):
        """
        Giả lập Thundering Herd: Lớp có max_capacity = 40, hiện tại đã có 35 SV (còn đúng 5 chỗ).
        Bắn đồng thời 100 request giữ chỗ -> Đúng 5 request thành công, 95 request bị chặn,
        bộ đếm cuối cùng dừng chính xác ở 40 (Zero Overselling).
        """
        class_id = uuid4()
        max_capacity = 40
        await self.fake_redis.set(CATALOG_READY_KEY, "1")
        await self.fake_redis.set(slot_counter_key(class_id), 35)

        results = await asyncio.gather(
            *[self.adapter.reserve_slot(class_id, max_capacity) for _ in range(100)]
        )

        success_count = sum(1 for r in results if r is True)
        fail_count = sum(1 for r in results if r is False)
        final_counter = int(await self.fake_redis.get(slot_counter_key(class_id)))

        self.assertEqual(success_count, 5, "Chỉ đúng 5 sinh viên được phép lấy 5 slot cuối!")
        self.assertEqual(fail_count, 95, "95 request còn lại phải bị từ chối ngay tại RAM!")
        self.assertEqual(final_counter, 40, "Sĩ số trên RAM không bao giờ được vượt quá max_capacity (40)!")

    async def test_compensating_transaction_release_slot_never_goes_negative(self):
        """Kiểm thử giao dịch bù trừ (release_slot) hoàn trả chỗ trống và không bao giờ giảm xuống âm."""
        class_id = uuid4()
        await self.fake_redis.set(slot_counter_key(class_id), 1)

        after_first = await self.adapter.release_slot(class_id)
        after_second = await self.adapter.release_slot(class_id)

        self.assertEqual(after_first, 0)
        self.assertEqual(after_second, 0)
        self.assertEqual(int(await self.fake_redis.get(slot_counter_key(class_id))), 0)

    async def test_per_student_mutex_blocks_multi_tab_spam(self):
        """Kiểm thử khóa phân tán theo sinh viên (lock:student:{id}) chặn 10 tab gửi cùng lúc."""
        student_id = uuid4()

        # 10 tab cùng bấm nút Đăng ký tại cùng 1 thời điểm
        lock_results = await asyncio.gather(
            *[self.adapter.acquire_student_lock(student_id, ttl=5) for _ in range(10)]
        )
        self.assertEqual(sum(1 for ok in lock_results if ok), 1)
        self.assertEqual(sum(1 for ok in lock_results if not ok), 9)

        # Sau khi giải phóng khóa, request tiếp theo của sinh viên được phép đi qua
        await self.adapter.release_student_lock(student_id)
        self.assertTrue(await self.adapter.acquire_student_lock(student_id, ttl=5))

    async def test_4_step_ram_crash_recovery_rebuilds_from_db_and_releases_lock(self):
        """
        Kiểm thử Giao thức Khôi phục Sự cố Sập RAM 4 bước (ADR-03):
        Khi Redis mất trắng (catalog:ready không tồn tại), reserve_slot tự động kích hoạt
        ensure_ram_ready(), đọc danh sách lớp từ DB để tái tạo slot:counter:* và catalog:class:*,
        bật lại catalog:ready=1 rồi giữ chỗ thành công.
        """
        class_id = uuid4()
        course = Course(
            id=10,
            code="INT3306",
            name="Kiến trúc phần mềm",
            credits=3,
            course_type="normal",
            prerequisite_course_ids=[1, 2],
        )
        cc = CourseClass(
            id=class_id,
            class_code="INT3306_1",
            course=course,
            room="302-G2",
            lecturer="TS. Nguyễn Văn A",
            max_capacity=40,
            current_capacity=39,
            schedules=[ClassSchedule(day_of_week=2, start_period=1, end_period=3)],
        )

        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [cc]

        # Ban đầu Redis trống rỗng (chưa có catalog:ready và chưa có slot:counter)
        self.assertEqual(await self.fake_redis.exists(CATALOG_READY_KEY), 0)

        # Sinh viên thứ 40 vào đăng ký -> kích hoạt 4-step Crash Recovery và lấy được slot thứ 40
        reserved = await self.adapter.reserve_slot(
            class_id=class_id,
            max_capacity=40,
            course_class_repo=mock_repo,
        )

        self.assertTrue(reserved)
        self.assertEqual(await self.fake_redis.exists(CATALOG_READY_KEY), 1)
        self.assertEqual(int(await self.fake_redis.get(slot_counter_key(class_id))), 40)
        self.assertEqual(await self.fake_redis.exists(REBUILD_LOCK_KEY), 0)

        cached_meta = json.loads(await self.fake_redis.get(catalog_class_key(class_id)))
        self.assertEqual(cached_meta["class_code"], "INT3306_1")
        self.assertEqual(cached_meta["prerequisite_ids"], [1, 2])

    async def test_singleflight_stampede_protection_when_another_worker_is_rebuilding(self):
        """
        Kiểm thử Singleflight Stampede Protection (ADR-03):
        Khi catalog:ready mất và Worker A đang giữ lock:rebuild_ram, Worker B gọi tới
        sẽ nhận ngoại lệ SystemRebuildInProgressError ngay lập tức thay vì đâm xuyên vào DB.
        """
        await self.fake_redis.set(REBUILD_LOCK_KEY, "1", nx=True, ex=10)
        mock_repo = AsyncMock()

        with self.assertRaises(SystemRebuildInProgressError):
            await self.adapter.ensure_ram_ready(mock_repo)

        mock_repo.get_all.assert_not_awaited()

    async def test_push_audit_log_enqueues_json_payload(self):
        """Kiểm thử đẩy nhật ký kiểm toán bất đồng bộ vào hàng đợi Redis LIST (audit:queue)."""
        student_id = uuid4()
        await self.adapter.push_audit_log(
            student_id=student_id,
            action="ENROLLED",
            class_code="INT3306_1",
            status="SUCCESS",
            ip_address="192.168.1.10",
            details={"credits": 3},
        )

        queue = self.fake_redis.lists.get(AUDIT_QUEUE_KEY, [])
        self.assertEqual(len(queue), 1)
        entry = json.loads(queue[0])
        self.assertEqual(entry["student_id"], str(student_id))
        self.assertEqual(entry["action"], "ENROLLED")
        self.assertEqual(entry["class_code"], "INT3306_1")
        self.assertEqual(entry["ip_address"], "192.168.1.10")


if __name__ == "__main__":
    unittest.main()
