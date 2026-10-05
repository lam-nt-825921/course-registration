from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.domain.entities.course import Course
from src.domain.repositories.course_repository import CourseRepository
from src.infrastructure.database.models import Course as CourseModel

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

    async def get_by_id_for_update(self, course_id: int) -> Optional[Course]:
        result = await self.session.execute(
            select(CourseModel).where(CourseModel.id == course_id).with_for_update()
        )
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def get_all(self) -> List[Course]:
        result = await self.session.execute(select(CourseModel))
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save(self, course: Course) -> Course:
        pass # Will be implemented in Task 3/4
