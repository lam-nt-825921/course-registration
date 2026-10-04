from typing import List, Optional
from sqlalchemy.orm import Session
from app.domain.entities.course import Course
from app.domain.repositories.course_repository import CourseRepository
from app.infrastructure.database.models import CourseModel

class SqlCourseRepository(CourseRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_entity(self, model: CourseModel) -> Course:
        return Course(
            id=model.id,
            code=model.code,
            name=model.name,
            credits=model.credits,
            max_slots=model.max_slots,
            registered_slots=model.registered_slots
        )

    def get_by_id(self, course_id: int) -> Optional[Course]:
        model = self.session.query(CourseModel).filter(CourseModel.id == course_id).first()
        return self._to_entity(model) if model else None

    def get_by_id_for_update(self, course_id: int) -> Optional[Course]:
        """
        Lấy Course và khóa row bằng SELECT ... FOR UPDATE.

        PostgreSQL sẽ giữ row lock cho đến khi transaction
        được commit hoặc rollback.
        """
        model = (
            self.session.query(CourseModel)
            .filter(CourseModel.id == course_id)
            .with_for_update()
            .first()
        )

        return self._to_entity(model) if model else None

    def get_all(self) -> List[Course]:
        models = self.session.query(CourseModel).all()
        return [self._to_entity(m) for m in models]

    def save(self, course: Course) -> Course:
        if course.id is None:
            model = CourseModel(
                code=course.code,
                name=course.name,
                credits=course.credits,
                max_slots=course.max_slots,
                registered_slots=course.registered_slots
            )
            self.session.add(model)
        else:
            model = self.session.query(CourseModel).filter(CourseModel.id == course.id).first()
            if model:
                model.registered_slots = course.registered_slots
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)
