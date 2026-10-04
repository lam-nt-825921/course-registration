from typing import Optional
from fastapi import Query
from src.domain.entities.course import Course
from src.domain.repositories.course_repository import CourseRepository

# CHÚ Ý: Tầng này KHÔNG import fastapi hay sqlalchemy
class CourseService:
    def __init__(self, course_repo: CourseRepository):
        self.course_repo = course_repo

    async def get_all_courses(self) -> list[Course]:
        return await self.course_repo.get_all()

    async def register_course(self, course_id: int, student_id: int) -> bool:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ValueError("Course not found")
        
        if not course.can_register():
            raise ValueError("Course is full")
        
        # In a real app, you would also save the student-course relationship
        course.registered_slots += 1
        await self.course_repo.save(course)
        return True
    async def get_active_courses(
            self,
            course_code: Optional[str] = None,
            day_of_week: Optional[int] = Query(None, ge=2, le=8),
            start_period: Optional[int] = Query(None, ge=1, le=12),
        ):
            return await self.repository.get_open_classes(
                course_code=course_code,
                day_of_week=day_of_week,
                start_period=start_period,
            )