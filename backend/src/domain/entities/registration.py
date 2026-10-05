from dataclasses import dataclass, field
from typing import List
from uuid import UUID

@dataclass
class ClassSchedule:
    day_of_week: int
    start_period: int
    end_period: int

    def conflicts_with(self, other: "ClassSchedule") -> bool:
        if self.day_of_week != other.day_of_week:
            return False
        return not (self.end_period < other.start_period or self.start_period > other.end_period)

@dataclass
class Course:
    id: int
    code: str
    credits: int
    course_type: str
    prerequisite_course_ids: List[int] = field(default_factory=list)

@dataclass
class CourseClass:
    id: UUID
    class_code: str
    course: Course
    max_capacity: int
    current_capacity: int = 0
    schedules: List[ClassSchedule] = field(default_factory=list)

    def can_register(self) -> bool:
        return self.current_capacity < self.max_capacity

@dataclass
class Enrollment:
    id: UUID
    student_id: UUID
    course_class: CourseClass
    status: str

@dataclass
class AcademicTranscript:
    course_id: int
    status: str

@dataclass
class Student:
    id: UUID
    enrollments: List[Enrollment] = field(default_factory=list)
    transcripts: List[AcademicTranscript] = field(default_factory=list)

    def get_total_registered_credits(self) -> int:
        return sum(e.course_class.course.credits for e in self.enrollments if e.course_class.course.course_type != "physical_education")
    
    def count_physical_education_courses(self) -> int:
        return sum(1 for e in self.enrollments if e.course_class.course.course_type == "physical_education")

    def has_passed_course(self, course_id: int) -> bool:
        return any(t.course_id == course_id and t.status == "passed" for t in self.transcripts)

    def has_schedule_conflict(self, new_schedules: List[ClassSchedule]) -> bool:
        for e in self.enrollments:
            for s1 in e.course_class.schedules:
                for s2 in new_schedules:
                    if s1.conflicts_with(s2):
                        return True
        return False
