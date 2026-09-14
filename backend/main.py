from fastapi import FastAPI
from app.api.endpoints import courses
from app.infrastructure.database.models import Base
from app.infrastructure.database.session import engine

# Tạo bảng tự động (chỉ dùng khi chưa có Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Course Registration API",
    description="API cho hệ thống đăng ký học phần (Kiến trúc phân tầng)",
    version="1.0.0"
)

app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
