from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.api.dependencies import get_current_admin
from src.api.schemas import MessageResponse
from src.infrastructure.database.session import get_db
from src.use_cases.admin_service import AdminService

router = APIRouter()

def get_admin_service(db: AsyncSession = Depends(get_db)):
    return AdminService(db)

class OpenSessionRequest(BaseModel):
    semester_code: str
    start_time: datetime
    end_time: datetime
    allowed_cohorts: List[str]

class RegistrationSessionResponse(BaseModel):
    id: int
    semester_code: str
    start_time: datetime
    end_time: datetime
    allowed_cohorts: List[str]
    is_cancelled: bool
    status: str

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    student_id: UUID
    action: str
    course_class_id: UUID
    timestamp: datetime
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True

@router.post("/sessions", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, summary="Mở phiên đăng ký mới")
async def open_registration_session(
    payload: OpenSessionRequest,
    service: AdminService = Depends(get_admin_service),
    current_admin: dict = Depends(get_current_admin)
):
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=400, detail="Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc")
    await service.create_session(payload.semester_code, payload.start_time, payload.end_time, payload.allowed_cohorts)
    return MessageResponse(message="Phiên đăng ký đã được mở thành công")

@router.get("/sessions", response_model=List[RegistrationSessionResponse], summary="Lấy danh sách các phiên đăng ký")
async def get_registration_sessions(
    service: AdminService = Depends(get_admin_service),
    current_admin: dict = Depends(get_current_admin)
):
    sessions = await service.get_sessions()
    result = []
    now = datetime.now()
    for s in sessions:
        if s.is_cancelled:
            stat = "Cancelled"
        elif now < s.start_time:
            stat = "Upcoming"
        elif s.start_time <= now <= s.end_time:
            stat = "Active"
        else:
            stat = "Ended"
            
        result.append(RegistrationSessionResponse(
            id=s.id,
            semester_code=s.semester.code,
            start_time=s.start_time,
            end_time=s.end_time,
            allowed_cohorts=s.allowed_cohorts,
            is_cancelled=s.is_cancelled,
            status=stat
        ))
    return result

@router.delete("/sessions/{session_id}", response_model=MessageResponse, summary="Hủy phiên đăng ký")
async def cancel_registration_session(
    session_id: int,
    service: AdminService = Depends(get_admin_service),
    current_admin: dict = Depends(get_current_admin)
):
    try:
        await service.cancel_session(session_id)
        return MessageResponse(message="Hủy phiên thành công")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/logs", response_model=List[AuditLogResponse], summary="Xem log thao tác sinh viên")
async def get_audit_logs(
    service: AdminService = Depends(get_admin_service),
    current_admin: dict = Depends(get_current_admin)
):
    logs = await service.get_logs()
    return [
        AuditLogResponse(
            id=l.id,
            student_id=l.student_id,
            course_class_id=l.course_class_id,
            action=l.action,
            timestamp=l.created_at,
            ip_address=l.ip_address
        ) for l in logs
    ]

@router.get("/cohorts", response_model=List[str], summary="Lấy danh sách khóa")
async def get_cohorts(
    service: AdminService = Depends(get_admin_service),
    current_admin: dict = Depends(get_current_admin)
):
    from sqlalchemy import select
    from src.infrastructure.database.models import Student
    result = await service.session.execute(select(Student.cohort).distinct())
    return [row[0] for row in result.all() if row[0]]
