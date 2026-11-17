import os

from redis.asyncio import Redis


_redis = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


def get_redis() -> Redis:
    return _redis
