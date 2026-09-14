from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.course import Course

class CourseRepository(ABC):
    @abstractmethod
    def get_by_id(self, course_id: int) -> Optional[Course]:
        pass

    @abstractmethod
    def get_all(self) -> List[Course]:
        pass

    @abstractmethod
    def save(self, course: Course) -> Course:
        pass
