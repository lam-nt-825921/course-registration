from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.infrastructure.database.session import get_db
from src.infrastructure.repositories.sql_course_repository import SQLCourseClassRepository, SQLStudentRepository, SQLEnrollmentRepository
from src.use_cases.course_service import CourseService
from src.application.security.auth import SECRET_KEY, ALGORITHM
from src.infrastructure.database.models import Student

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_course_service(db: AsyncSession = Depends(get_db)):
    class_repo = SQLCourseClassRepository(db)
    student_repo = SQLStudentRepository(db)
    enrollment_repo = SQLEnrollmentRepository(db)
    return CourseService(class_repo, student_repo, enrollment_repo)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return {"email": email, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_student(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.get("role") != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không đủ quyền truy cập (Yêu cầu quyền Sinh viên)")
    
    # Query student.user_id
    result = await db.execute(select(Student).where(Student.student_code == current_user["email"]))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinh viên không tồn tại")
    
    current_user["student_id"] = student.user_id
    return current_user

def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không đủ quyền truy cập (Yêu cầu quyền Quản trị viên)")
    return current_user
