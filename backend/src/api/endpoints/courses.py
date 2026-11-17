from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.use_cases.course_service import CourseService
from src.api.dependencies import get_course_service, get_current_student
from src.api.schemas import CourseClassResponse, RegisterCourseRequest, MessageResponse, EnrollmentHistoryResponse, PaginatedCourseClassResponse
from src.application.security.rate_limit import limiter
from src.infrastructure.cache.catalog_read_adapter import CatalogReadAdapter
from src.infrastructure.database.session import get_db
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_keys import CATALOG_READY_KEY, slot_counter_key, student_state_key

router = APIRouter()


async def invalidate_registration_cache(service, student_id, class_id):
    # Publish invalidation only after PostgreSQL has committed. The next catalog
    # read warms the missing counter with SETNX from the committed DB value.
    await service.course_class_repo.session.commit()
    await get_redis().delete(
        student_state_key(str(student_id)), slot_counter_key(str(class_id)), CATALOG_READY_KEY,
    )

@router.get("/", response_model=PaginatedCourseClassResponse, summary="Lấy & Lọc Lớp học phần hợp lệ")
async def get_courses(
    request: Request,
    keyword: Optional[str] = Query(None, description="Tìm theo tên môn/mã môn"),
    can_register: Optional[bool] = Query(None, description="Chỉ hiện lớp còn slot"),
    day_of_week: Optional[int] = Query(None, description="Lọc theo thứ (2-8)"),
    course_type: Optional[str] = Query(None, description="Loại môn: normal, physical_education..."),
    page: int = Query(1, description="Số trang", ge=1),
    size: int = Query(20, description="Kích thước trang", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_student)
):
    return await CatalogReadAdapter.query_courses_from_ram(
        student_id=current_user["student_id"],
        keyword=keyword, 
        can_register=can_register, 
        day_of_week=day_of_week, 
        course_type=course_type,
        page=page,
        size=size,
        db=db,
    )

@router.get("/my-schedule", response_model=List[CourseClassResponse], summary="Xem TKB & Preview")
async def get_my_schedule(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_student)
):
    return await CatalogReadAdapter.get_my_schedule_from_ram(
        student_id=current_user["student_id"], db=db,
    )

@router.post("/register", response_model=MessageResponse, summary="Ghi nhận đăng ký")
@limiter.limit("10/second")
async def register_course(
    request: Request,
    payload: RegisterCourseRequest, 
    service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_student)
):
    try:
        await service.register_course(payload.course_class_id, current_user["student_id"])
        await invalidate_registration_cache(service, current_user["student_id"], payload.course_class_id)
        return MessageResponse(message="Registration successful")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/register/{class_id}", response_model=MessageResponse, summary="Hủy đăng ký")
async def cancel_registration(
    class_id: UUID,
    request: Request,
    service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_student)
):
    try:
        student_id = current_user["student_id"]
        await service.cancel_registration(class_id, student_id)
        await invalidate_registration_cache(service, student_id, class_id)
        return MessageResponse(message="Cancellation successful")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/enrollments/history", response_model=List[EnrollmentHistoryResponse], summary="Lịch sử đăng ký học các kỳ")
async def get_enrollment_history(
    request: Request,
    service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_student)
):
    student_id = current_user["student_id"]
    history = await service.get_enrollment_history(student_id)
    # mock mapping for now, or real mapping
    return history
