from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.course import Course

class CourseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, course_id: int) -> Optional[Course]:
        pass

    @abstractmethod
    async def get_by_id_for_update(self, course_id: int) -> Optional[Course]:
        pass

    @abstractmethod
    async def get_all(self) -> List[Course]:
        pass

    @abstractmethod
    async def save(self, course: Course) -> Course:
        pass
