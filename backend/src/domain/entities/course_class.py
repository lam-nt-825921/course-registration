from dataclasses import dataclass
from src.domain.entities.class_schedule import ClassSchedule
from typing import List
@dataclass
class CourseClass:
    id: str
    class_code: str
    course_id: int
    course_code: str
    credits: int
    max_capacity: int
    current_capacity: int
    schedules: List[ClassSchedule]

    def can_register(self) -> bool:
        return self.current_capacity < self.max_capacity