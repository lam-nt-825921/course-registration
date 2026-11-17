import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from src.api.endpoints.admin import router, get_admin_service
from src.api.dependencies import get_current_admin


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/api/admin")
    service = AsyncMock()
    service.get_logs.return_value = []
    app.dependency_overrides[get_admin_service] = lambda: service
    app.dependency_overrides[get_current_admin] = lambda: {"role": "admin"}
    return app


@pytest.mark.asyncio
async def test_open_session(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/admin/sessions", json={
            "semester_code": "20241", "start_time": "2026-01-01T00:00:00",
            "end_time": "2026-01-02T00:00:00", "allowed_cohorts": ["K68"],
        })
    assert response.status_code == 201
    assert response.json()["message"]


@pytest.mark.asyncio
async def test_get_audit_logs(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/logs")
    assert response.status_code == 200
    assert response.json() == []
