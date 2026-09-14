from fastapi import Depends
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.infrastructure.repositories.sql_course_repository import SqlCourseRepository
from app.use_cases.course_service import CourseService

def get_course_service(db: Session = Depends(get_db)):
    repo = SqlCourseRepository(db)
    return CourseService(repo)
