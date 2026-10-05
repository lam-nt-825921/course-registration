from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Optional
from uuid import UUID
from src.use_cases.course_service import CourseService
from src.api.dependencies import get_course_service, get_current_student
from src.api.schemas import CourseClassResponse, RegisterCourseRequest, MessageResponse, EnrollmentHistoryResponse
from src.application.security.rate_limit import limiter

router = APIRouter()

@router.get("/", response_model=List[CourseClassResponse], summary="Lấy & Lọc Lớp học phần hợp lệ")
async def get_courses(
    request: Request,
    keyword: Optional[str] = Query(None, description="Tìm theo tên môn/mã môn"),
    can_register: Optional[bool] = Query(None, description="Chỉ hiện lớp còn slot"),
    day_of_week: Optional[int] = Query(None, description="Lọc theo thứ (2-8)"),
    course_type: Optional[str] = Query(None, description="Loại môn: normal, physical_education..."),
    service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_student)
):
    classes = await service.get_all_courses(keyword, can_register, day_of_week, course_type)
    return [
        CourseClassResponse(
            id=c.id,
            class_code=c.class_code,
            course_code=c.course.code,
            credits=c.course.credits,
            course_type=c.course.course_type,
            max_capacity=c.max_capacity,
            current_capacity=c.current_capacity,
            schedules=c.schedules
        ) for c in classes
    ]

@router.get("/my-schedule", response_model=List[CourseClassResponse], summary="Xem TKB & Preview")
async def get_my_schedule(
    request: Request,
    service: CourseService = Depends(get_course_service),
    current_user: dict = Depends(get_current_student)
):
    # In a real app we parse student_id from current_user JWT. For now assuming it's available or mocking it.
    student_id = current_user["student_id"] 
    classes = await service.get_my_schedule(student_id)
    return [
        CourseClassResponse(
            id=c.id,
            class_code=c.class_code,
            course_code=c.course.code,
            credits=c.course.credits,
            course_type=c.course.course_type,
            max_capacity=c.max_capacity,
            current_capacity=c.current_capacity,
            schedules=c.schedules
        ) for c in classes
    ]

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
