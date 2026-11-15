"""Quản lý phiên 30 phút đăng nhập + 20 phút chờ (cooldown) trên Redis."""
import json
import os
import time
import uuid

from fastapi import HTTPException, status

from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_keys import (
    ONLINE_STUDENTS_ZSET,
    SESSION_LIMIT_TOGGLE_KEY,
    session_lease_key,
    student_state_key,
)

ACTIVE_DURATION_SEC = 30 * 60      # 30 phút đăng nhập
COOLDOWN_DURATION_SEC = 20 * 60    # 20 phút chờ
MAX_CONCURRENT_USERS = int(os.getenv("MAX_CONCURRENT_USERS", "2000"))


class SessionLeaseAdapter:
    @staticmethod
    async def is_limit_enabled() -> bool:
        val = await get_redis().get(SESSION_LIMIT_TOGGLE_KEY)
        return val != "0"  # mặc định BẬT ("1" hoặc chưa có key)

    @staticmethod
    async def set_limit_enabled(enabled: bool) -> None:
        await get_redis().set(SESSION_LIMIT_TOGGLE_KEY, "1" if enabled else "0")

    @staticmethod
    async def acquire_or_resume_lease(student_id: str) -> dict:
        """Trả về {"session_id", "remaining_sec"} hoặc ném 403/429."""
        r = get_redis()
        now = time.time()

        if not await SessionLeaseAdapter.is_limit_enabled():
            return {"session_id": str(uuid.uuid4()), "remaining_sec": ACTIVE_DURATION_SEC}

        key = session_lease_key(student_id)
        raw = await r.get(key)
        if raw:
            lease = json.loads(raw)
            if now < lease["active_until"]:
                # Còn trong 30 phút: dùng tiếp thời gian còn lại, không phạt cooldown
                remaining = int(lease["active_until"] - now)
                await r.zadd(ONLINE_STUDENTS_ZSET, {student_id: lease["active_until"]})
                return {"session_id": lease["session_id"], "remaining_sec": max(1, remaining)}
            if now < lease["cooldown_until"]:
                wait_sec = int(lease["cooldown_until"] - now)
                mins, secs = divmod(wait_sec, 60)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Phiên làm việc của bạn đã kết thúc. Vui lòng đợi {mins} phút {secs} giây.",
                )

        # Đăng nhập mới: kiểm tra số người online đồng thời
        await r.zremrangebyscore(ONLINE_STUDENTS_ZSET, "-inf", now)
        if await r.zcard(ONLINE_STUDENTS_ZSET) >= MAX_CONCURRENT_USERS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Phòng đăng ký đang đầy, vui lòng chờ trong giây lát",
            )

        session_id = str(uuid.uuid4())
        active_until = now + ACTIVE_DURATION_SEC
        cooldown_until = active_until + COOLDOWN_DURATION_SEC
        lease = {"session_id": session_id, "active_until": active_until, "cooldown_until": cooldown_until}
        await r.setex(key, ACTIVE_DURATION_SEC + COOLDOWN_DURATION_SEC, json.dumps(lease))
        await r.zadd(ONLINE_STUDENTS_ZSET, {student_id: active_until})
        return {"session_id": session_id, "remaining_sec": ACTIVE_DURATION_SEC}

    @staticmethod
    async def explicit_logout(student_id: str) -> None:
        r = get_redis()
        now = time.time()
        await r.zrem(ONLINE_STUDENTS_ZSET, student_id)
        await r.delete(student_state_key(student_id))

        key = session_lease_key(student_id)
        if await SessionLeaseAdapter.is_limit_enabled():
            lease = {"session_id": "logged_out", "active_until": now, "cooldown_until": now + COOLDOWN_DURATION_SEC}
            await r.setex(key, COOLDOWN_DURATION_SEC, json.dumps(lease))
        else:
            await r.delete(key)

    @staticmethod
    async def verify_active_lease(student_id: str) -> None:
        if not await SessionLeaseAdapter.is_limit_enabled():
            return
        raw = await get_redis().get(session_lease_key(student_id))
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên đăng nhập 30 phút đã hết hạn hoặc bạn đã đăng xuất",
            )
        if time.time() >= json.loads(raw)["active_until"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên đăng nhập 30 phút đã hết hạn hoặc bạn đã đăng xuất",
            )
