from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.use_cases.course_service import CourseService
from src.api.dependencies import get_course_service

router = APIRouter()

@router.get("/")
async def get_courses(service: CourseService = Depends(get_course_service)):
    # Tầng API chỉ làm nhiệm vụ parse request và gọi Use Case
    return await service.get_all_courses()

@router.get("/")
async def get_active_courses(
    course_code: Optional[str] = None,
    day_of_week: Optional[int] = Query(default=None, ge=2, le=8),
    start_period: Optional[int] = Query(default=None, ge=1, le=12),
    service: CourseService = Depends(get_course_service),
):
    return await service.get_active_courses(
        course_code=course_code,
        day_of_week=day_of_week,
        start_period=start_period,
    )    

@router.post("/register")
async def register_course(
    course_code: str,
    class_code: str,
    student_id: str,
    service: CourseService = Depends(get_course_service),
):
    return await service.register_course(
        course_code=course_code,
        class_code=class_code,
        student_id=student_id,
    )

@router.post("/{course_id}/register")
async def register_course(course_id: int, student_id: int, service: CourseService = Depends(get_course_service)):
    try:
        await service.register_course(course_id, student_id)
        return {"message": "Registration successful"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
