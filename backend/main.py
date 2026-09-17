from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.api.endpoints import courses
from src.api.auth import endpoints as auth
from src.application.security.rate_limit import limiter

app = FastAPI(
    title="Course Registration API",
    description="API cho hệ thống đăng ký học phần (Kiến trúc phân tầng)",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
