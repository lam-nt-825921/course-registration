"""Ghi audit log ngầm: request chỉ LPUSH vào Redis, worker gom lô xuống PostgreSQL."""
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_keys import AUDIT_QUEUE_KEY

logger = logging.getLogger(__name__)

BATCH_SIZE = 200
FLUSH_INTERVAL_SEC = 2


async def enqueue_audit_log(
    student_id: Optional[str],
    action: str,
    course_class_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Đẩy 1 sự kiện vào queue. Không bao giờ làm hỏng request nếu Redis lỗi."""
    event = {
        "student_id": str(student_id) if student_id else None,
        "course_class_id": str(course_class_id) if course_class_id else None,
        "action": action,
        "ip_address": ip_address,
        "ts": datetime.utcnow().isoformat(),
    }
    try:
        await get_redis().lpush(AUDIT_QUEUE_KEY, json.dumps(event))
    except Exception:
        logger.warning("Không đẩy được audit event %s vào Redis", action, exc_info=True)


def _parse_uuid(value) -> Optional[UUID]:
    return UUID(value) if value else None


def _to_model(raw: str):
    from src.infrastructure.database.models import AuditLog

    d = json.loads(raw)
    raw_cid = d.get("course_class_id") or (d.get("details") or {}).get("course_class_id")
    raw_ts = d.get("ts") or d.get("timestamp")
    created_at = None
    if raw_ts:
        dt = datetime.fromisoformat(raw_ts)
        created_at = dt.replace(tzinfo=None) if dt.tzinfo else dt
    return AuditLog(
        student_id=_parse_uuid(d.get("student_id")),
        course_class_id=_parse_uuid(raw_cid),
        action=d["action"],
        ip_address=d.get("ip_address"),
        created_at=created_at,
    )


async def _insert(logs: list) -> None:
    from src.infrastructure.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            session.add_all(logs)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def flush_once() -> int:
    """Rút tối đa BATCH_SIZE sự kiện và ghi 1 lô duy nhất. Trả về số phần tử đã rút."""
    raws: Optional[List[str]] = await get_redis().rpop(AUDIT_QUEUE_KEY, BATCH_SIZE)
    if not raws:
        return 0

    pairs = []
    for raw in raws:
        try:
            pairs.append((raw, _to_model(raw)))
        except Exception:
            logger.warning("Bỏ qua audit event sai định dạng: %r", raw)

    if not pairs:
        return len(raws)

    try:
        await _insert([m for _, m in pairs])
    except Exception:
        # Lô lỗi (vd. FK student không tồn tại): thử từng dòng để không mất log hợp lệ
        logger.warning("Bulk insert audit_logs lỗi, thử ghi từng dòng", exc_info=True)
        for raw, _ in pairs:
            try:
                await _insert([_to_model(raw)])
            except Exception:
                logger.error("Bỏ audit event không ghi được: %r", raw, exc_info=True)
    return len(raws)


async def audit_flush_loop() -> None:
    """Chạy ngầm trong lifespan: mỗi 2 giây gom lô ghi xuống DB."""
    try:
        while True:
            try:
                # Xả hết hàng đợi nếu đang dồn (mỗi vòng 1 lô)
                while await flush_once() >= BATCH_SIZE:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.error("Audit worker lỗi, sẽ thử lại", exc_info=True)
            await asyncio.sleep(FLUSH_INTERVAL_SEC)
    except asyncio.CancelledError:
        # Tắt server: xả nốt phần còn lại để không mất log
        try:
            while await flush_once() >= BATCH_SIZE:
                pass
        except Exception:
            logger.error("Không xả được audit queue khi tắt", exc_info=True)
        raise
