import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis

from src.domain.entities.registration import (
    AcademicTranscript,
    ClassSchedule,
    Course,
    CourseClass,
    Enrollment,
    Student,
)
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_keys import (
    AUDIT_QUEUE_KEY,
    CATALOG_READY_KEY,
    REBUILD_LOCK_KEY,
    catalog_class_key,
    slot_counter_key,
    student_lock_key,
    student_state_key,
)

logger = logging.getLogger(__name__)

# Atomic Lua Script kiểm tra và giữ chỗ trong 1 nhịp CPU (0 Race Condition / 0 Overselling)
LUA_RESERVE_SLOT = """
local current = redis.call('GET', KEYS[1])
if current == false then
    return -1
end
if tonumber(current) < tonumber(ARGV[1]) then
    redis.call('INCR', KEYS[1])
    return 1
else
    return 0
end
"""

# Atomic Lua Script hoàn trả slot (Compensating Transaction) đảm bảo không bao giờ âm
LUA_RELEASE_SLOT = """
local current = redis.call('GET', KEYS[1])
if current == false then
    return 0
end
if tonumber(current) > 0 then
    return redis.call('DECR', KEYS[1])
end
return 0
"""


class SystemRebuildInProgressError(RuntimeError):
    """Ngoại lệ báo hiệu hệ thống đang khôi phục bộ nhớ đệm RAM (Singleflight Stampede Protection)."""
    pass


class SlotReservationAdapter:
    """
    Adapter quản lý giữ chỗ nguyên tử trên Redis (Atomic Slot Gate),
    khóa chống gửi trùng theo sinh viên (Per-Student Mutex),
    khôi phục sự cố sập RAM 4 bước (4-Step Crash Recovery - ADR-03),
    và đồng bộ trạng thái sinh viên / nhật ký kiểm toán bất đồng bộ.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis: redis.Redis = redis_client or get_redis()

    @staticmethod
    def serialize_course_class(cc: CourseClass) -> dict[str, Any]:
        """Chuyển đổi thực thể CourseClass sang cấu trúc JSON chuẩn của catalog:class:{id}."""
        return {
            "id": str(cc.id),
            "class_code": cc.class_code,
            "course_id": cc.course.id,
            "course_code": cc.course.code,
            "course_name": cc.course.name,
            "credits": cc.course.credits,
            "course_type": cc.course.course_type,
            "room": cc.room,
            "lecturer": cc.lecturer,
            "max_capacity": cc.max_capacity,
            "prerequisite_ids": list(getattr(cc.course, "prerequisite_course_ids", []) or []),
            "schedules": [
                {
                    "day_of_week": s.day_of_week,
                    "start_period": s.start_period,
                    "end_period": s.end_period,
                }
                for s in (cc.schedules or [])
            ],
        }

    @staticmethod
    def deserialize_course_class(data: dict[str, Any], current_capacity: int = 0) -> CourseClass:
        """Tái tạo thực thể Domain CourseClass từ JSON lưu trên Redis."""
        course = Course(
            id=int(data["course_id"]),
            code=data["course_code"],
            name=data["course_name"],
            credits=int(data["credits"]),
            course_type=data["course_type"],
            prerequisite_course_ids=list(data.get("prerequisite_ids", [])),
        )
        schedules = [
            ClassSchedule(
                day_of_week=int(s["day_of_week"]),
                start_period=int(s["start_period"]),
                end_period=int(s["end_period"]),
            )
            for s in data.get("schedules", [])
        ]
        return CourseClass(
            id=UUID(str(data["id"])),
            class_code=data["class_code"],
            course=course,
            room=data.get("room") or "",
            lecturer=data.get("lecturer") or "",
            max_capacity=int(data["max_capacity"]),
            current_capacity=int(current_capacity),
            schedules=schedules,
        )

    async def acquire_student_lock(self, student_id: UUID | str, ttl: int = 5) -> bool:
        """
        Khóa phân tán ngắn hạn theo sinh viên (SET lock:student:{id} 1 NX EX 5)
        ngăn chặn hành vi mở 10 tab bấm đăng ký cùng lúc.
        """
        key = student_lock_key(student_id)
        acquired = await self.redis.set(key, "1", nx=True, ex=ttl)
        return bool(acquired)

    async def release_student_lock(self, student_id: UUID | str) -> None:
        """Giải phóng khóa phân tán của sinh viên ngay trong khối finally."""
        key = student_lock_key(student_id)
        await self.redis.delete(key)

    async def ensure_ram_ready(self, course_class_repo: Optional[Any] = None) -> bool:
        """
        Giao thức Khôi phục Sự cố Sập RAM 4 bước (ADR-03):
        1. Kiểm tra cờ catalog:ready trên Redis.
        2. Nếu mất cờ, tranh quyền Singleflight bằng SET lock:rebuild_ram 1 NX EX 10.
        3. Các worker không lấy được lock sẽ từ chối tạm thời (tránh Cache Stampede vào DB).
        4. Worker giữ lock đọc bảng CourseClasses từ DB để tái tạo bộ đếm slot:counter và catalog:class.
        """
        exists = await self.redis.exists(CATALOG_READY_KEY)
        if exists:
            return True

        if course_class_repo is None:
            return False

        # Tranh quyền tái tạo RAM (Singleflight Lock)
        is_leader = await self.redis.set(REBUILD_LOCK_KEY, "1", nx=True, ex=10)
        if not is_leader:
            raise SystemRebuildInProgressError(
                "Hệ thống đang đồng bộ lại bộ nhớ đệm, vui lòng thử lại sau giây lát."
            )

        try:
            raw_res = await course_class_repo.get_all(page=1, size=1000)
            all_classes = (
                raw_res.get("items", []) if isinstance(raw_res, dict) else list(raw_res or [])
            )
            pipe = self.redis.pipeline(transaction=True)
            for cc in all_classes:
                cid = str(cc.id)
                pipe.set(
                    catalog_class_key(cid),
                    json.dumps(self.serialize_course_class(cc)),
                )
                pipe.set(slot_counter_key(cid), int(cc.current_capacity))
            pipe.set(CATALOG_READY_KEY, "1")
            await pipe.execute()
            return True
        finally:
            await self.redis.delete(REBUILD_LOCK_KEY)

    async def reserve_slot(
        self,
        class_id: UUID | str,
        max_capacity: int,
        course_class_repo: Optional[Any] = None,
        initial_capacity: Optional[int] = None,
    ) -> bool:
        """
        Thực thi Lua Script giữ chỗ nguyên tử trên Redis.
        - Trả về True nếu giữ chỗ thành công (INCR).
        - Trả về False nếu lớp đã đầy (current >= max_capacity).
        - Nếu key slot:counter:{class_id} chưa tồn tại (return -1), tự động kích hoạt
          khôi phục RAM (ADR-03) hoặc nạp lazy từ DB rồi thử lại 1 lần.
        """
        key = slot_counter_key(class_id)
        res = await self.redis.eval(LUA_RESERVE_SLOT, 1, key, int(max_capacity))

        if res == -1:
            if course_class_repo is not None:
                await self.ensure_ram_ready(course_class_repo)
                if not await self.redis.exists(key):
                    cc = await course_class_repo.get_by_id(UUID(str(class_id)))
                    if cc is not None:
                        await self.redis.setnx(key, int(cc.current_capacity))
            elif initial_capacity is not None:
                await self.redis.setnx(key, int(initial_capacity))
            else:
                return False

            res = await self.redis.eval(LUA_RESERVE_SLOT, 1, key, int(max_capacity))

        return int(res) == 1

    async def release_slot(self, class_id: UUID | str) -> int:
        """
        Giao dịch bù trừ (Compensating Transaction) hoặc khi hủy môn:
        Giảm nguyên tử bộ đếm slot:counter:{class_id} trên Redis (không bao giờ âm).
        """
        key = slot_counter_key(class_id)
        res = await self.redis.eval(LUA_RELEASE_SLOT, 1, key)
        return int(res or 0)

    async def get_or_load_course_class(
        self,
        class_id: UUID,
        course_class_repo: Optional[Any] = None,
    ) -> Optional[CourseClass]:
        """
        Đọc thông tin lớp học phần từ catalog:class:{id} và slot:counter:{id} trên RAM.
        Nếu cache miss và có truyền repository, tự động nạp Lazy từ PostgreSQL.
        """
        cid = str(class_id)
        raw_meta = await self.redis.get(catalog_class_key(cid))
        raw_slot = await self.redis.get(slot_counter_key(cid))

        if raw_meta is not None and raw_slot is not None:
            return self.deserialize_course_class(json.loads(raw_meta), int(raw_slot))

        if course_class_repo is None:
            return None

        cc = await course_class_repo.get_by_id(class_id)
        if not cc:
            return None

        await self.redis.set(catalog_class_key(cid), json.dumps(self.serialize_course_class(cc)))
        await self.redis.setnx(slot_counter_key(cid), int(cc.current_capacity))
        await self.redis.setnx(CATALOG_READY_KEY, "1")
        return cc

    async def get_or_load_student(
        self,
        student_id: UUID,
        student_repo: Optional[Any] = None,
    ) -> Optional[Student]:
        """
        Đọc hồ sơ học tập sinh viên từ student:state:{student_id} trên RAM.
        Nếu cache miss, nạp từ student_repo.get_by_id(student_id) và lưu TTL 1800s.
        """
        key = student_state_key(student_id)
        raw = await self.redis.get(key)
        if raw:
            data = json.loads(raw)
            enrollments = [
                Enrollment(
                    id=UUID(e.get("enrollment_id", str(uuid4()))),
                    student_id=UUID(str(data["student_id"])),
                    course_class=self.deserialize_course_class(e["course_class"]),
                    status=e.get("status", "enrolled"),
                )
                for e in data.get("enrollments", [])
            ]
            transcripts = [
                AcademicTranscript(course_id=int(t["course_id"]), status=t["status"])
                for t in data.get("transcript", [])
            ]
            return Student(
                id=UUID(str(data["student_id"])),
                cohort=data.get("cohort", ""),
                enrollments=enrollments,
                transcripts=transcripts,
            )

        if student_repo is None:
            return None

        student = await student_repo.get_by_id(student_id)
        if not student:
            return None

        state = {
            "student_id": str(student.id),
            "cohort": student.cohort,
            "enrollments": [
                {
                    "enrollment_id": str(e.id),
                    "status": e.status,
                    "course_class": self.serialize_course_class(e.course_class),
                }
                for e in student.enrollments
            ],
            "transcript": [
                {"course_id": t.course_id, "status": t.status}
                for t in student.transcripts
            ],
        }
        await self.redis.set(key, json.dumps(state), ex=1800)
        return student

    async def invalidate_student_state(self, student_id: UUID | str) -> None:
        """Xóa cache student:state:{student_id} sau khi thay đổi đăng ký để đồng bộ tức thì."""
        await self.redis.delete(student_state_key(student_id))

    async def push_audit_log(
        self,
        student_id: UUID | str,
        action: str,
        class_code: str,
        status: str = "SUCCESS",
        ip_address: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Đẩy nhật ký kiểm toán bất đồng bộ vào hàng đợi Redis LIST (LPUSH audit:queue)
        phục vụ NFR-04 mà không chặn luồng ghi chính.
        """
        payload = {
            "student_id": str(student_id),
            "action": action,
            "status": status,
            "class_code": class_code,
            "ip_address": ip_address,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self.redis.lpush(AUDIT_QUEUE_KEY, json.dumps(payload))
        except Exception as exc:
            logger.warning("Không thể đẩy log vào audit:queue trên Redis: %s", exc)
