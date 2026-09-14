from fastapi import APIRouter, Depends, HTTPException
from app.use_cases.course_service import CourseService
from app.api.dependencies import get_course_service

router = APIRouter()

@router.get("/")
def get_courses(service: CourseService = Depends(get_course_service)):
    # Tầng API chỉ làm nhiệm vụ parse request và gọi Use Case
    return service.get_all_courses()

@router.post("/{course_id}/register")
def register_course(course_id: int, student_id: int, service: CourseService = Depends(get_course_service)):
    try:
        service.register_course(course_id, student_id)
        return {"message": "Registration successful"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
