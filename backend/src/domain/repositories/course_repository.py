from abc import ABC, abstractmethod
from typing import List, Optional
from fastapi import Query
from src.domain.entities.course import Course

class CourseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, course_id: int) -> Optional[Course]:
        pass

    @abstractmethod
    async def get_all(self) -> List[Course]:
        pass

    @abstractmethod
    async def save(self, course: Course) -> Course:
        pass

    @abstractmethod
    async def get_active_courses( self,
        course_code: Optional[str] = None,
        day_of_week: Optional[int]  = Query(None, ge=2, le=8),
        start_period: Optional[int] = Query(None, ge=1, le=12)):
        pass
