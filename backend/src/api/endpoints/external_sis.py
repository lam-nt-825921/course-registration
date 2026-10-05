from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/courses", summary="Mock SIS: Lấy danh mục học phần")
async def get_sis_courses(semester_code: str) -> List[Dict]:
    return [{"course_code": "INT3110", "name": "Kiến trúc phần mềm", "credits": 3}]

@router.get("/students", summary="Mock SIS: Lấy hồ sơ sinh viên")
async def get_sis_students(cohort: str) -> List[Dict]:
    return [{"student_code": "20020000", "name": "Nguyen Van A", "cohort": "K68"}]
