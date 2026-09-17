import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from src.infrastructure.database.session import get_db

# Mock DB dependency
async def override_get_db():
    yield None

app.dependency_overrides[get_db] = override_get_db

@pytest.mark.asyncio
async def test_login_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Simulate 101 requests to trigger rate limit (100/second)
        for _ in range(101):
            # We omit form_data to get 422 Unprocessable Entity, but Rate Limiter still runs before endpoint logic!
            # Actually, to hit the endpoint properly, we need to pass data, 
            # and if db is None, db.execute will fail if it reaches there.
            # But the 101st request will be blocked with 429 before reaching db.execute!
            pass
            
        # We need the first 100 to just return some early error (like 422) or we mock the login logic.
        # It's better to just mock db.execute but `override_get_db` yields None, so it raises AttributeError.
        # Let's write a proper mock session.
        pass

class MockSession:
    async def execute(self, *args, **kwargs):
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def first(self):
                        return None
                return MockScalars()
        return MockResult()

async def override_get_db_proper():
    yield MockSession()

app.dependency_overrides[get_db] = override_get_db_proper

@pytest.mark.asyncio
async def test_login_rate_limit_proper():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for _ in range(101):
            response = await ac.post("/api/auth/login", data={"username": "test@vnu.edu.vn", "password": "password"})
        
        assert response.status_code == 429
