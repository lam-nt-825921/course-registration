from typing import List, Optional
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.domain.entities.course import Course
from src.domain.entities.class_schedule import ClassSchedule
from src.domain.entities.course_class import CourseClass
from src.domain.repositories.course_repository import CourseRepository
from src.infrastructure.database.models import (
            ClassSchedule as ClassScheduleModel,
            Course as CourseModel, 
            RegistrationSession as RegistrationSessionModel, 
            Semester as SemesterModel, 
            CourseClass as CourseClassModel
)
from datetime import datetime
class SqlCourseRepository(CourseRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: CourseModel) -> Course:
        # Dummy mapping cho đến khi implement Task 3/4
        return Course(
            id=model.id,
            code=model.course_code,
            name="TBD",
            credits=model.credits,
            max_slots=0,
            registered_slots=0
        )

    async def get_by_id(self, course_id: int) -> Optional[Course]:
        result = await self.session.execute(select(CourseModel).where(CourseModel.id == course_id))
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def get_all(self) -> List[Course]:
        result = await self.session.execute(select(CourseModel))
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save(self, course: Course) -> Course:
        pass # Will be implemented in Task 3/4

    async def get_active_courses( self,
        course_code: Optional[str] = None,
        day_of_week: Optional[int]  = Query(None, ge=2, le=8),
        start_period: Optional[int] = Query(None, ge=1, le=12)):
        now = datetime.now()

        query = (
            select(
                CourseClassModel,
                CourseModel,
                SemesterModel,
                RegistrationSessionModel,
            )
            .join(
                CourseModel,
                CourseClassModel.course_id == CourseModel.id
            )
            .join(
                SemesterModel,
                CourseClassModel.semester_id == SemesterModel.id
            )
            .join(
                RegistrationSessionModel,
                RegistrationSessionModel.semester_id
                == SemesterModel.id
            )
            .where(
                SemesterModel.is_active == True,
                RegistrationSessionModel.start_time <= now,
                RegistrationSessionModel.end_time > now,
            )
        )
        if course_code:
            query = query.where(
                CourseModel.course_code.ilike(f"%{course_code}%")
            )
        result = await self.session.execute(query)

        rows = result.all()
        course_classes = []

        for course_class, course, semester, registration_session in rows:

            schedule_query = select(ClassScheduleModel).where(
                ClassScheduleModel.course_class_id
                == course_class.id
            )

            if day_of_week is not None:
                schedule_query = schedule_query.where(
                    ClassScheduleModel.day_of_week
                    == day_of_week
                )

            if start_period is not None:
                schedule_query = schedule_query.where(
                    ClassScheduleModel.start_period
                    == start_period
                )

            schedule_result = await self.session.execute(
                schedule_query
            )

            schedules = schedule_result.scalars().all()

            if (day_of_week is not None or start_period is not None) \
                    and not schedules:
                continue

            schedule_entities = [
                ClassSchedule(
                    day_of_week=schedule.day_of_week,
                    start_period=schedule.start_period,
                    end_period=schedule.end_period,
                )
                for schedule in schedules
            ]

            course_class_entity = CourseClass(
                id=str(course_class.id),
                class_code=course_class.class_code,
                course_id=course.id,
                course_code=course.course_code,
                credits=course.credits,
                max_capacity=course_class.max_capacity,
                current_capacity=course_class.current_capacity,
                schedules=schedule_entities,
            )

            course_classes.append(course_class_entity)
        if not course_classes:
            return "Không có lớp phù hợp"
        return course_classes