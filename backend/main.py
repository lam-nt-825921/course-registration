from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

import os

# Lấy FRONTEND_URL từ env, mặc định cho phép localhost:3000 và 127.0.0.1:3000
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url, 
        "http://localhost:3000", 
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])
from src.api.endpoints import admin, external_sis

app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

app.include_router(external_sis.router, prefix="/api/external-sis", tags=["External SIS Mock"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
