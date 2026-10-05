from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.api.dependencies import get_current_admin
from src.api.schemas import MessageResponse

router = APIRouter()

class OpenSessionRequest(BaseModel):
    semester_code: str
    start_time: datetime
    end_time: datetime
    allowed_cohorts: List[str]

class AuditLogResponse(BaseModel):
    id: int
    student_id: str
    action: str
    course_class_id: str
    timestamp: datetime
    ip_address: str

    class Config:
        from_attributes = True

@router.post("/sessions", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, summary="Mở phiên đăng ký & Đồng bộ SIS")
async def open_registration_session(
    payload: OpenSessionRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    UC-A1: Admin tạo phiên đăng ký mới.
    Hành động này sẽ gọi ngầm sang Module External SIS để fetch danh mục Lớp học phần mới nhất.
    """
    # Logic: calls external SIS mock, saves RegistrationSession, populates CourseClasses...
    return MessageResponse(message="Phiên đăng ký đã được mở và đồng bộ dữ liệu thành công")

@router.get("/logs", response_model=List[AuditLogResponse], summary="Xem log thao tác sinh viên")
async def get_audit_logs(
    student_id: Optional[str] = None,
    class_id: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    """
    UC-A2: Truy xuất mọi thao tác Đăng ký/Hủy của sinh viên.
    """
    # Mock data return
    return []

@router.get("/logs/abnormal", response_model=List[dict], summary="Cảnh báo thao tác bất thường (Bot/Mua bán slot)")
async def get_abnormal_logs(
    time_threshold_ms: int = 500,
    current_admin: dict = Depends(get_current_admin)
):
    """
    UC-A3: Phân tích log tìm ra các cặp thao tác Hủy-Đăng ký trên cùng 1 slot 
    diễn ra cách nhau ít hơn time_threshold_ms (nghi vấn dùng tool chuyển slot).
    """
    # Mock data return
    return [
        {
            "course_class_id": "uuid-class-123",
            "dropped_by": "student_A",
            "registered_by": "student_B",
            "time_gap_ms": 45,
            "severity": "HIGH",
            "reason": "Chuyển nhượng slot chớp nhoáng (45ms)"
        }
    ]
