import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from main import app
from src.api.dependencies import get_course_service, get_current_student
from src.application.security.rate_limit import limiter

client = TestClient(app)

class MockCourseService:
    async def get_all_courses(self, keyword=None, can_register=None, day_of_week=None, course_type=None):
        return []
        
    async def register_course(self, class_id, student_id):
        if str(class_id) == "12345678-1234-4234-8234-123456789012":
            raise ValueError("Lớp học phần đã hết chỗ")
        return True
        
    async def get_my_schedule(self, student_id):
        return []
        
    async def cancel_registration(self, class_id, student_id):
        if str(class_id) == "12345678-1234-4234-8234-123456789012":
            raise ValueError("Bạn chưa đăng ký lớp này")
        return True
        
    async def get_enrollment_history(self, student_id):
        return []

async def override_get_current_student():
    return {"email": "student@vnu.edu.vn", "role": "student", "student_id": "11111111-1111-1111-1111-111111111111"}

app.dependency_overrides[get_course_service] = lambda: MockCourseService()
app.dependency_overrides[get_current_student] = override_get_current_student

def test_get_courses():
    response = client.get("/api/courses/")
    assert response.status_code == 200
    assert response.json() == []

def test_register_course_success():
    payload = {
        "student_id": str(uuid4()),
        "course_class_id": str(uuid4())
    }
    response = client.post("/api/courses/register", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "Registration successful", "detail": None}

def test_register_course_fails():
    payload = {
        "student_id": str(uuid4()),
        "course_class_id": "12345678-1234-4234-8234-123456789012"
    }
    response = client.post("/api/courses/register", json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": "Lớp học phần đã hết chỗ"}

def test_get_my_schedule():
    response = client.get("/api/courses/my-schedule")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_cancel_registration():
    response = client.delete(f"/api/courses/register/{str(uuid4())}")
    assert response.status_code == 200
    assert response.json() == {"message": "Cancellation successful", "detail": None}

def test_cancel_registration_fails():
    response = client.delete("/api/courses/register/12345678-1234-4234-8234-123456789012")
    assert response.status_code == 400
    assert response.json() == {"detail": "Bạn chưa đăng ký lớp này"}
    
def test_get_enrollment_history():
    response = client.get("/api/courses/enrollments/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
