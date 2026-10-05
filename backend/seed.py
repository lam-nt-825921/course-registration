import asyncio
import os
import sys

# Add path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.database.models import (
    Course, CourseTypeEnum, User, RoleEnum, Student, 
    Semester, RegistrationSession, CourseClass
)
from src.application.security.auth import get_password_hash

async def seed_data():
    async with AsyncSessionLocal() as session:
        # Check if we already have users
        result = await session.execute(select(User))
        if result.scalars().first() is not None:
            print("Dữ liệu đã tồn tại. Bỏ qua seeding.")
            return

        print("Đang thêm Seed Data cho Hệ thống...")
        
        # 1. Tạo User & Student (cho phép đăng nhập bằng mã sinh viên)
        # Sử dụng dummy_password giống như frontend gọi API mặc định
        hashed_pw = get_password_hash("dummy_password")
        
        student_user = User(
            email="20020000", # Lấy email làm username (mã SV) cho tiện
            password_hash=hashed_pw,
            role=RoleEnum.student
        )
        session.add(student_user)
        await session.flush() # Lấy student_user.id
        
        student_profile = Student(
            user_id=student_user.id,
            student_code="20020000",
            cohort="QH-2020-I/CQ"
        )
        session.add(student_profile)

        # 2. Tạo Semester
        semester = Semester(
            code="20241",
            is_active=True
        )
        session.add(semester)
        await session.flush()
        
        # 3. Tạo Registration Session (phiên đăng ký) cho K65
        reg_session = RegistrationSession(
            semester_id=semester.id,
            allowed_cohorts=["QH-2020-I/CQ", "K65"]
        )
        session.add(reg_session)

        # 4. Tạo Courses
        c1 = Course(course_code="INT3306", credits=3, course_type=CourseTypeEnum.normal)
        c2 = Course(course_code="INT3110", credits=3, course_type=CourseTypeEnum.normal)
        c3 = Course(course_code="INT3202", credits=3, course_type=CourseTypeEnum.normal)
        session.add_all([c1, c2, c3])
        await session.flush()
        
        # 5. Tạo CourseClasses (Lớp môn học) để sinh viên đăng ký
        # Lớp Kiến trúc phần mềm (30 slot)
        cc1 = CourseClass(
            class_code="INT3306_1",
            course_id=c1.id,
            semester_id=semester.id,
            max_capacity=30,
            current_capacity=0
        )
        
        # Lớp Phân tích thiết kế (50 slot)
        cc2 = CourseClass(
            class_code="INT3110_1",
            course_id=c2.id,
            semester_id=semester.id,
            max_capacity=50,
            current_capacity=0
        )
        
        # Lớp Hệ quản trị CSDL (rất ít slot để test overselling)
        cc3 = CourseClass(
            class_code="INT3202_1",
            course_id=c3.id,
            semester_id=semester.id,
            max_capacity=2,
            current_capacity=0
        )
        session.add_all([cc1, cc2, cc3])
        
        # Hoàn tất
        await session.commit()
        print("Seed Data thành công! Mã sinh viên: 20020000 | Mật khẩu: dummy_password")

if __name__ == "__main__":
    asyncio.run(seed_data())
