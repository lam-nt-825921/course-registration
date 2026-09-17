from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.session import get_db
from src.infrastructure.repositories.sql_course_repository import SqlCourseRepository
from src.use_cases.course_service import CourseService

def get_course_service(db: AsyncSession = Depends(get_db)):
    repo = SqlCourseRepository(db)
    return CourseService(repo)
