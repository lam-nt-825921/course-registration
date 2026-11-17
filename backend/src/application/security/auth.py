import asyncio
import os
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Chạy BCrypt trên threadpool để không chặn event loop."""
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)

async def get_password_hash_async(password: str) -> str:
    return await asyncio.to_thread(get_password_hash, password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
