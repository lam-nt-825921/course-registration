from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from uuid import UUID
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.infrastructure.database.session import get_db
from src.infrastructure.repositories.sql_course_repository import SQLCourseClassRepository, SQLStudentRepository, SQLEnrollmentRepository
from src.infrastructure.cache.slot_reservation_adapter import SlotReservationAdapter
from src.use_cases.course_service import CourseService
from src.application.security.auth import SECRET_KEY, ALGORITHM
from src.infrastructure.database.models import Student
from src.infrastructure.cache.session_lease_adapter import SessionLeaseAdapter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_course_service(db: AsyncSession = Depends(get_db)):
    class_repo = SQLCourseClassRepository(db)
    student_repo = SQLStudentRepository(db)
    enrollment_repo = SQLEnrollmentRepository(db)
    slot_adapter = SlotReservationAdapter()
    return CourseService(class_repo, student_repo, enrollment_repo, slot_adapter=slot_adapter)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = {"email": email, "role": payload.get("role")}
    # Claims nhúng sẵn trong JWT (không cần query DB)
    for claim in ("student_id", "cohort", "major_id", "session_id"):
        if claim in payload:
            user[claim] = payload[claim]
    return user

async def get_current_student(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.get("role") != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không đủ quyền truy cập (Yêu cầu quyền Sinh viên)")

    if current_user.get("student_id"):
        # lấy thẳng từ JWT, 0 câu lệnh SQL
        try:
            student_id = UUID(str(current_user["student_id"]))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    else:
        #fallback query DB 1 lần
        result = await db.execute(select(Student).where(Student.student_code == current_user["email"]))
        student = result.scalars().first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinh viên không tồn tại")
        student_id = student.user_id
        current_user["cohort"] = student.cohort
        current_user["major_id"] = student.major_id

    # Kiểm tra còn trong 30 phút đăng nhập và chưa đăng xuất (Redis)
    await SessionLeaseAdapter.verify_active_lease(str(student_id))

    current_user["student_id"] = student_id
    return current_user

def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không đủ quyền truy cập (Yêu cầu quyền Quản trị viên)")
    return current_user
