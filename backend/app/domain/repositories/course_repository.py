from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.course import Course

class CourseRepository(ABC):
    @abstractmethod
    def get_by_id(self, course_id: int) -> Optional[Course]:
        pass

    @abstractmethod
    def get_by_id_for_update(self, course_id: int) -> Optional[Course]:
        """
        Lấy Course và khóa row trong database để tránh
        race condition khi nhiều người đăng ký cùng lúc.
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Course]:
        pass

    @abstractmethod
    def save(self, course: Course) -> Course:
        pass
