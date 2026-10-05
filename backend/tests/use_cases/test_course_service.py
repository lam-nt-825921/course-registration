import pytest
from uuid import uuid4
from src.domain.entities.registration import Course, CourseClass, Student, ClassSchedule, AcademicTranscript, Enrollment
from src.use_cases.course_service import CourseService

class MockCourseClassRepository:
    def __init__(self):
        self.classes = {}
    async def get_all(self):
        return list(self.classes.values())
    async def get_by_id_for_update(self, class_id):
        return self.classes.get(class_id)
    async def save(self, course_class):
        self.classes[course_class.id] = course_class

class MockStudentRepository:
    def __init__(self):
        self.students = {}
    async def get_by_id(self, student_id):
        return self.students.get(student_id)

class MockEnrollmentRepository:
    async def create(self, enrollment):
        pass

@pytest.fixture
def service_and_repos():
    class_repo = MockCourseClassRepository()
    student_repo = MockStudentRepository()
    enrollment_repo = MockEnrollmentRepository()
    service = CourseService(class_repo, student_repo, enrollment_repo)
    return service, class_repo, student_repo

@pytest.mark.asyncio
async def test_register_success(service_and_repos):
    service, class_repo, student_repo = service_and_repos
    student_id = uuid4()
    class_id = uuid4()
    
    student = Student(id=student_id)
    student_repo.students[student_id] = student
    
    course = Course(id=1, code="INT101", credits=3, course_type="normal", prerequisite_course_ids=[])
    course_class = CourseClass(id=class_id, course=course, max_capacity=50, current_capacity=0)
    class_repo.classes[class_id] = course_class
    
    result = await service.register_course(class_id, student_id)
    assert result is True
    assert course_class.current_capacity == 1

@pytest.mark.asyncio
async def test_register_fails_when_full(service_and_repos):
    service, class_repo, student_repo = service_and_repos
    student_id = uuid4()
    class_id = uuid4()
    
    student = Student(id=student_id)
    student_repo.students[student_id] = student
    
    course = Course(id=1, code="INT101", credits=3, course_type="normal")
    course_class = CourseClass(id=class_id, course=course, max_capacity=50, current_capacity=50) # Full
    class_repo.classes[class_id] = course_class
    
    with pytest.raises(ValueError, match="Lớp học phần đã hết chỗ"):
        await service.register_course(class_id, student_id)

@pytest.mark.asyncio
async def test_register_fails_credits_limit(service_and_repos):
    service, class_repo, student_repo = service_and_repos
    student_id = uuid4()
    class_id = uuid4()
    
    course_heavy = Course(id=1, code="HEAVY", credits=25, course_type="normal")
    enrolled_class = CourseClass(id=uuid4(), course=course_heavy, max_capacity=50)
    enrollment = Enrollment(id=uuid4(), student_id=student_id, course_class=enrolled_class, status="enrolled")
    
    student = Student(id=student_id, enrollments=[enrollment]) # Already has 25 credits
    student_repo.students[student_id] = student
    
    new_course = Course(id=2, code="NEW", credits=3, course_type="normal")
    new_class = CourseClass(id=class_id, course=new_course, max_capacity=50, current_capacity=0)
    class_repo.classes[class_id] = new_class
    
    with pytest.raises(ValueError, match="Vượt quá giới hạn tín chỉ tối đa"):
        await service.register_course(class_id, student_id)

@pytest.mark.asyncio
async def test_register_fails_missing_prerequisite(service_and_repos):
    service, class_repo, student_repo = service_and_repos
    student_id = uuid4()
    class_id = uuid4()
    
    student = Student(id=student_id) # No transcripts
    student_repo.students[student_id] = student
    
    # Needs prerequisite course ID 99
    new_course = Course(id=2, code="ADVANCED", credits=3, course_type="normal", prerequisite_course_ids=[99])
    new_class = CourseClass(id=class_id, course=new_course, max_capacity=50)
    class_repo.classes[class_id] = new_class
    
    with pytest.raises(ValueError, match="Chưa đạt môn tiên quyết"):
        await service.register_course(class_id, student_id)

@pytest.mark.asyncio
async def test_register_fails_time_conflict(service_and_repos):
    service, class_repo, student_repo = service_and_repos
    student_id = uuid4()
    class_id = uuid4()
    
    # Existing class on Monday (2), periods 1-3
    course1 = Course(id=1, code="C1", credits=3, course_type="normal")
    class1 = CourseClass(id=uuid4(), course=course1, max_capacity=50, schedules=[ClassSchedule(2, 1, 3)])
    enrollment = Enrollment(id=uuid4(), student_id=student_id, course_class=class1, status="enrolled")
    
    student = Student(id=student_id, enrollments=[enrollment])
    student_repo.students[student_id] = student
    
    # New class on Monday (2), periods 2-4 (Conflicts!)
    new_course = Course(id=2, code="C2", credits=3, course_type="normal")
    new_class = CourseClass(id=class_id, course=new_course, max_capacity=50, schedules=[ClassSchedule(2, 2, 4)])
    class_repo.classes[class_id] = new_class
    
    with pytest.raises(ValueError, match="Trùng lịch học"):
        await service.register_course(class_id, student_id)
