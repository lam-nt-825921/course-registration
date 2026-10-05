import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from src.infrastructure.database.session import get_db
from src.api.dependencies import get_current_user
from fastapi import Request

class MockUser:
    def __init__(self, email, password_hash):
        self.email = email
        self.password_hash = password_hash
        self.role = "student"

class MockSession:
    async def execute(self, *args, **kwargs):
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def first(self):
                        from src.application.security.auth import get_password_hash
                        # Trả về User mock với mật khẩu cũ là 'old'
                        return MockUser("student@vnu.edu.vn", get_password_hash("old"))
                return MockScalars()
        return MockResult()
        
    def add(self, *args, **kwargs):
        pass
        
    async def commit(self):
        pass

async def override_get_db_proper():
    yield MockSession()

async def override_get_current_user():
    return {"email": "student@vnu.edu.vn", "role": "student"}

app.dependency_overrides[get_db] = override_get_db_proper
app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.mark.asyncio
async def test_change_password_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/api/auth/password", json={"old_password": "old", "new_password": "new_pass"})
        assert response.status_code == 200
        assert response.json()["message"] == "Đổi mật khẩu thành công"

@pytest.mark.asyncio
async def test_change_password_fail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/api/auth/password", json={"old_password": "wrong", "new_password": "new_pass"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Mật khẩu cũ không chính xác"
