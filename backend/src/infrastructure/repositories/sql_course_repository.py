from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.domain.entities.registration import Course, CourseClass, ClassSchedule, Student, AcademicTranscript, Enrollment
from src.infrastructure.database.models import (
    CourseClass as CourseClassModel, 
    Student as StudentModel,
    Enrollment as EnrollmentModel,
    Course as CourseModel
)

class SQLCourseClassRepository:
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, model: CourseClassModel) -> CourseClass:
        schedules = [ClassSchedule(s.day_of_week, s.start_period, s.end_period) for s in model.schedules]
        # mapping prerequisites manually or fetching it. Assume prerequisite_course_ids is list of int
        prereqs = [p.prereq_id for p in model.course.prerequisites] if model.course.prerequisites else []
        
        course_domain = Course(
            id=model.course.id,
            code=model.course.course_code,
            name=model.course.name,
            credits=model.course.credits,
            course_type=model.course.course_type.value if hasattr(model.course.course_type, 'value') else model.course.course_type,
            prerequisite_course_ids=prereqs
        )
        return CourseClass(
            id=model.id,
            class_code=model.class_code,
            course=course_domain,
            room=model.room or "",
            lecturer=model.lecturer or "",
            max_capacity=model.max_capacity,
            current_capacity=model.current_capacity,
            schedules=schedules
        )

    async def get_by_id_for_update(self, class_id: UUID) -> Optional[CourseClass]:
        stmt = select(CourseClassModel).options(
            selectinload(CourseClassModel.course).selectinload(CourseModel.prerequisites),
            selectinload(CourseClassModel.schedules)
        ).where(CourseClassModel.id == class_id).with_for_update()
        
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return self._to_domain(model) if model else None

    async def save(self, course_class: CourseClass):
        # Update current capacity
        stmt = select(CourseClassModel).where(CourseClassModel.id == course_class.id)
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        if model:
            model.current_capacity = course_class.current_capacity
            self.session.add(model)
            await self.session.flush()

    async def get_all(self, student_id=None, keyword=None, can_register=None, day_of_week=None, course_type=None, page=1, size=20) -> dict:
        stmt = select(CourseClassModel).options(
            selectinload(CourseClassModel.course).selectinload(CourseModel.prerequisites),
            selectinload(CourseClassModel.schedules)
        ).join(CourseClassModel.course)

        # Filters
        if keyword:
            stmt = stmt.where(
                (CourseClassModel.class_code.ilike(f"%{keyword}%")) |
                (CourseModel.course_code.ilike(f"%{keyword}%")) |
                (CourseModel.name.ilike(f"%{keyword}%"))
            )
        
        if can_register is not None:
            if can_register:
                stmt = stmt.where(CourseClassModel.current_capacity < CourseClassModel.max_capacity)

        if day_of_week:
            from src.infrastructure.database.models import ClassSchedule as ClassScheduleModel
            stmt = stmt.join(CourseClassModel.schedules).where(ClassScheduleModel.day_of_week == day_of_week)

        if course_type:
            stmt = stmt.where(CourseModel.course_type == course_type)
        
        if student_id:
            student_stmt = select(StudentModel.major_id).where(StudentModel.user_id == student_id)
            student_res = await self.session.execute(student_stmt)
            major_id = student_res.scalar()

            if major_id:
                from src.infrastructure.database.models import MajorCourse
                # Môn đã được gắn với 1 ngành nào đó
                mapped_courses = select(MajorCourse.course_id)
                
                stmt = stmt.outerjoin(
                    MajorCourse, CourseModel.id == MajorCourse.course_id
                ).where(
                    (MajorCourse.major_id == major_id) | 
                    (~CourseModel.id.in_(mapped_courses))
                )

        # Pagination
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.order_by(CourseClassModel.class_code).offset((page - 1) * size).limit(size)
        
        result = await self.session.execute(stmt)
        models = result.scalars().unique().all()
        
        items = [self._to_domain(m) for m in models]
        pages = (total + size - 1) // size if total else 0
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "next": page + 1 if page < pages else None,
            "prev": page - 1 if page > 1 else None
        }


class SQLStudentRepository:
    def __init__(self, session: Session):
        self.session = session

    async def get_by_id(self, student_id: UUID) -> Optional[Student]:
        stmt = select(StudentModel).options(
            selectinload(StudentModel.enrollments).selectinload(EnrollmentModel.course_class).selectinload(CourseClassModel.course).selectinload(CourseModel.prerequisites),
            selectinload(StudentModel.enrollments).selectinload(EnrollmentModel.course_class).selectinload(CourseClassModel.schedules),
            selectinload(StudentModel.transcripts)
        ).where(StudentModel.user_id == student_id)
        
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        
        if not model:
            return None
            
        transcripts = [AcademicTranscript(t.course_id, t.status.value if hasattr(t.status, 'value') else t.status) for t in model.transcripts]
        enrollments = []
        
        # Need to reconstruct CourseClass for enrollments
        for e in model.enrollments:
            schedules = [ClassSchedule(s.day_of_week, s.start_period, s.end_period) for s in e.course_class.schedules]
            course_domain = Course(
                id=e.course_class.course.id,
                code=e.course_class.course.course_code,
                name=e.course_class.course.name,
                credits=e.course_class.course.credits,
                course_type=e.course_class.course.course_type.value if hasattr(e.course_class.course.course_type, 'value') else e.course_class.course.course_type
            )
            cc_domain = CourseClass(
                id=e.course_class.id,
                class_code=e.course_class.class_code,
                course=course_domain,
                room=e.course_class.room or "",
                lecturer=e.course_class.lecturer or "",
                max_capacity=e.course_class.max_capacity,
                current_capacity=e.course_class.current_capacity,
                schedules=schedules
            )
            enrollments.append(Enrollment(id=e.id, student_id=e.student_id, course_class=cc_domain, status=e.status.value if hasattr(e.status, 'value') else e.status))
            
        return Student(id=model.user_id, cohort=model.cohort, enrollments=enrollments, transcripts=transcripts)

class SQLEnrollmentRepository:
    def __init__(self, session: Session):
        self.session = session
        
    async def create(self, enrollment: Enrollment):
        db_enrollment = EnrollmentModel(
            id=enrollment.id,
            student_id=enrollment.student_id,
            course_class_id=enrollment.course_class.id,
            status=enrollment.status
        )
        self.session.add(db_enrollment)
        await self.session.flush()
    async def cancel_enrollment(self, student_id: UUID, course_class_id: UUID) -> bool:
        stmt = select(EnrollmentModel).where(EnrollmentModel.student_id == student_id, EnrollmentModel.course_class_id == course_class_id, EnrollmentModel.status == 'enrolled')
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        if not model:
            return False
        model.status = 'cancelled'
        self.session.add(model)
        await self.session.flush()
        return True
