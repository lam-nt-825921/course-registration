from app.domain.entities.course import Course
from app.domain.repositories.course_repository import CourseRepository

# CHÚ Ý: Tầng này KHÔNG import fastapi hay sqlalchemy
class CourseService:
    def __init__(self, course_repo: CourseRepository):
        self.course_repo = course_repo

    def get_all_courses(self) -> list[Course]:
        return self.course_repo.get_all()

    def register_course(self, course_id: int, student_id: int) -> bool:
        # course = self.course_repo.get_by_id(course_id)
        # Lấy Course kèm row lock để chống overselling.
        course = self.course_repo.get_by_id_for_update(course_id)
        if not course:
            raise ValueError("Course not found")
        
        if not course.can_register():
            raise ValueError("Course is full")
        
        # In a real app, you would also save the student-course relationship
        course.registered_slots += 1
        self.course_repo.save(course)
        return True
