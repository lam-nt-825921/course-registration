"""Rate limit chặn spam trên Redis + auto-blacklist + chống ngập log 429."""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import jwt
from starlette.responses import JSONResponse

from src.application.security.auth import ALGORITHM, SECRET_KEY
from src.infrastructure.cache.audit_worker import enqueue_audit_log
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_keys import blacklist_key, ratelimit_key, spam_hits_key

logger = logging.getLogger(__name__)

SPAM_HITS_BLACKLIST_THRESHOLD = 50
SPAM_HITS_WINDOW_SEC = 60
BLACKLIST_TTL_SEC = 900  # 15 phút

BLACKLIST_MESSAGE = "Tài khoản/IP bị khóa tạm thời 15 phút do thao tác bất thường"
TOO_MANY_MESSAGE = "Quá nhiều yêu cầu, vui lòng thử lại sau"


@dataclass
class RateLimitDecision:
    message: str
    retry_after: int


class RedisRateLimiter:
    @staticmethod
    async def check(
        actor_key: str,
        limit: int,
        student_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[RateLimitDecision]:
        """None nếu cho qua; RateLimitDecision nếu phải trả 429."""
        r = get_redis()
        second = int(time.time())
        count_key = ratelimit_key(actor_key, second)

        pipe = r.pipeline(transaction=False)
        pipe.exists(blacklist_key(actor_key))
        pipe.incr(count_key)
        pipe.expire(count_key, 2)
        blacklisted, count, _ = await pipe.execute()

        if blacklisted:
            return RateLimitDecision(BLACKLIST_MESSAGE, BLACKLIST_TTL_SEC)

        if count <= limit:
            return None

        pipe = r.pipeline(transaction=False)
        pipe.incr(spam_hits_key(actor_key))
        pipe.expire(spam_hits_key(actor_key), SPAM_HITS_WINDOW_SEC, nx=True)
        hits, _ = await pipe.execute()

        # Chỉ ghi audit ở lần vi phạm đầu tiên và khi chạm ngưỡng khóa
        if hits == 1 or hits == SPAM_HITS_BLACKLIST_THRESHOLD:
            await enqueue_audit_log(student_id, "RATE_LIMIT_EXCEEDED", ip_address=ip_address)

        if hits >= SPAM_HITS_BLACKLIST_THRESHOLD:
            await r.setex(blacklist_key(actor_key), BLACKLIST_TTL_SEC, "SPAM_BOT")
            return RateLimitDecision(BLACKLIST_MESSAGE, BLACKLIST_TTL_SEC)

        return RateLimitDecision(TOO_MANY_MESSAGE, 1)


# (method, tiền tố path, scope, giới hạn req/giây)
RULES = [
    ("POST", "/api/courses/register", "enroll", 10),
    ("DELETE", "/api/courses/register", "enroll", 10),
    ("POST", "/api/auth/login", "login", 100),
]


def _match_rule(method: str, path: str):
    path = path.rstrip("/") or "/"
    for m, prefix, scope, limit in RULES:
        if method == m and (path == prefix or path.startswith(prefix + "/")):
            return scope, limit
    return None


def _identify_actor(scope_name: str, scope: dict):
    """Trả về (actor_key, student_id, ip). Có JWT hợp lệ -> theo sinh viên, ngược lại theo IP."""
    client = scope.get("client")
    ip = client[0] if client else "unknown"
    headers = dict(scope.get("headers") or [])
    auth = headers.get(b"authorization", b"").decode("latin-1")
    if scope_name != "login" and auth.lower().startswith("bearer "):
        try:
            payload = jwt.decode(auth[7:], SECRET_KEY, algorithms=[ALGORITHM])
            sid = payload.get("student_id") or payload.get("sub")
            if sid:
                return f"{scope_name}:user:{sid}", payload.get("student_id"), ip
        except jwt.PyJWTError:
            pass
    return f"{scope_name}:ip:{ip}", None, ip


class RedisRateLimitMiddleware:
    """ASGI middleware thuần (nhẹ hơn BaseHTTPMiddleware). Fail-open nếu Redis lỗi."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        rule = _match_rule(scope["method"], scope["path"])
        if rule is None:
            return await self.app(scope, receive, send)

        scope_name, limit = rule
        actor_key, student_id, ip = _identify_actor(scope_name, scope)
        try:
            decision = await RedisRateLimiter.check(actor_key, limit, student_id=student_id, ip_address=ip)
        except Exception:
            logger.warning("Rate limiter Redis lỗi, cho qua (fail-open)", exc_info=True)
            decision = None

        if decision is not None:
            response = JSONResponse(
                {"detail": decision.message},
                status_code=429,
                headers={"Retry-After": str(decision.retry_after)},
            )
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)
