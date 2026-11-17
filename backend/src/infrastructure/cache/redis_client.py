import os
import redis.asyncio as redis

# Dùng REDIS_URL từ Docker, fallback localhost:6379 cho môi trường dev
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_pool = redis.ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=True,
    max_connections=100,
)


def get_redis() -> redis.Redis:
    """Trả về Redis async client sử dụng chung ConnectionPool."""
    return redis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """Đóng toàn bộ kết nối trong Redis ConnectionPool khi tắt ứng dụng."""
    await redis_pool.disconnect()

