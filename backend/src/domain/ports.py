"""
Domain Repository & Concurrency Ports (Hexagonal / Clean Architecture Interfaces).
Tuyệt đối không import SQLAlchemy, Redis hay bất kỳ thư viện hạ tầng nào tại tầng Domain (NFR-03).
"""
from typing import Optional, Protocol
from uuid import UUID
from src.domain.entities.registration import CourseClass, Enrollment, Student


class ICourseClassRepository(Protocol):
    async def get_by_id(self, class_id: UUID) -> Optional[CourseClass]:
        ...

    async def get_by_id_for_update(self, class_id: UUID) -> Optional[CourseClass]:
        ...

    async def save(self, course_class: CourseClass) -> None:
        ...

    async def increment_capacity_atomic(self, class_id: UUID) -> bool:
        ...

    async def decrement_capacity_atomic(self, class_id: UUID) -> bool:
        ...

    async def is_session_open_for_cohort(self, cohort: str) -> bool:
        ...

    async def record_audit_log(
        self,
        student_id: UUID,
        course_class_id: UUID,
        action: str,
        ip_address: Optional[str] = None,
    ) -> None:
        ...

    async def get_all(
        self,
        student_id: Optional[UUID] = None,
        keyword: Optional[str] = None,
        can_register: Optional[bool] = None,
        day_of_week: Optional[int] = None,
        course_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        ...


class IStudentRepository(Protocol):
    async def get_by_id(self, student_id: UUID) -> Optional[Student]:
        ...


class IEnrollmentRepository(Protocol):
    async def create(self, enrollment: Enrollment) -> None:
        ...

    async def cancel_enrollment(self, student_id: UUID, course_class_id: UUID) -> bool:
        ...

    async def is_already_enrolled(self, student_id: UUID, course_class_id: UUID) -> bool:
        ...
