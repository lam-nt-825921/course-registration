from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import User, Student
from src.application.security.auth import (
    verify_password_async,
    get_password_hash_async,
    create_access_token,
)
from src.application.security.rate_limit import limiter
from src.infrastructure.cache.session_lease_adapter import SessionLeaseAdapter
from src.infrastructure.cache.audit_worker import enqueue_audit_log

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=Token)
@limiter.limit("100/second")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    # BCrypt chạy trên threadpool, không chặn event loop
    if not user or not await verify_password_async(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = getattr(user.role, "value", user.role)
    claims = {"sub": user.email, "role": role}
    expires_delta = None
    student_id = None

    if role == "student":
        student = (await db.execute(select(Student).where(Student.user_id == user.id))).scalars().first()
        if not student:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hồ sơ sinh viên không tồn tại")
        student_id = str(student.user_id)

        # Phiên 30p đăng nhập + 20p chờ (ném 403 nếu đang cooldown, 429 nếu phòng đầy)
        lease = await SessionLeaseAdapter.acquire_or_resume_lease(student_id)
        claims.update({
            "student_id": student_id,
            "cohort": student.cohort,
            "major_id": student.major_id,
            "session_id": lease["session_id"],
        })
        expires_delta = timedelta(seconds=lease["remaining_sec"])

    access_token = create_access_token(data=claims, expires_delta=expires_delta)

    if student_id:
        await enqueue_audit_log(
            student_id, "LOGIN", ip_address=request.client.host if request.client else None
        )
    return {"access_token": access_token, "token_type": "bearer"}

from src.api.schemas import ChangePasswordRequest, MessageResponse
from src.api.dependencies import get_current_user, get_current_student

@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, current_user: dict = Depends(get_current_student)):
    student_id = str(current_user["student_id"])
    await SessionLeaseAdapter.explicit_logout(student_id)
    await enqueue_audit_log(
        student_id, "LOGOUT", ip_address=request.client.host if request.client else None
    )
    return MessageResponse(message="Đăng xuất thành công. Bạn có thể đăng nhập lại sau 20 phút.")

@router.get("/session-limit")
async def get_session_limit(current_user: dict = Depends(get_current_user)):
    """Cho frontend biết giới hạn phiên 30p+20p đang bật hay tắt (để ẩn/hiện đồng hồ)."""
    return {"limit_enabled": await SessionLeaseAdapter.is_limit_enabled()}

@router.put("/password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == current_user["email"]))
    user = result.scalars().first()

    if not user or not await verify_password_async(request.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không chính xác"
        )

    user.password_hash = await get_password_hash_async(request.new_password)
    db.add(user)
    await db.commit()

    return MessageResponse(message="Đổi mật khẩu thành công")
