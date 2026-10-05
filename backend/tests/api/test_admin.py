import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from src.api.dependencies import get_current_admin

async def override_get_current_admin():
    return {"email": "admin@vnu.edu.vn", "role": "admin"}

app.dependency_overrides[get_current_admin] = override_get_current_admin

@pytest.mark.asyncio
async def test_open_session():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "semester_code": "20241",
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-02T00:00:00",
            "allowed_cohorts": ["K68"]
        }
        response = await ac.post("/api/admin/sessions", json=payload)
        assert response.status_code == 201
        assert response.json()["message"] == "Phiên đăng ký đã được mở và đồng bộ dữ liệu thành công"

@pytest.mark.asyncio
async def test_get_audit_logs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/logs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_abnormal_logs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/logs/abnormal?time_threshold_ms=500")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        if len(response.json()) > 0:
            assert "course_class_id" in response.json()[0]
