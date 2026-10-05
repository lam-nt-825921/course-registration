import asyncio
import os
import sys
import random

# Add path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.database.models import (
    Course, CourseTypeEnum, User, RoleEnum, Student, 
    Semester, RegistrationSession, CourseClass, ClassSchedule
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
        
        hashed_pw = get_password_hash("dummy_password")
        
        # 1. Tạo Admin
        admin_user = User(
            email="admin@vnu.edu.vn",
            password_hash=hashed_pw,
            role=RoleEnum.admin
        )
        session.add(admin_user)
        
        # 2. Tạo User & Student mẫu
        student_user = User(
            email="20020000",
            password_hash=hashed_pw,
            role=RoleEnum.student
        )
        session.add(student_user)
        await session.flush()
        
        student_profile = Student(
            user_id=student_user.id,
            student_code="20020000",
            cohort="QH-2020-I/CQ"
        )
        session.add(student_profile)

        # Tạo thêm 50 sinh viên ngẫu nhiên để test
        for i in range(1, 51):
            s_code = f"2002{i:04d}"
            s_user = User(
                email=s_code,
                password_hash=hashed_pw,
                role=RoleEnum.student
            )
            session.add(s_user)
            await session.flush()
            s_profile = Student(
                user_id=s_user.id,
                student_code=s_code,
                cohort="QH-2020-I/CQ"
            )
            session.add(s_profile)

        # 3. Tạo Semester
        semester = Semester(
            code="20241",
            is_active=True
        )
        session.add(semester)
        await session.flush()
        
        from datetime import datetime, timedelta
        # 4. Tạo Registration Session (phiên đăng ký) cho K65
        now = datetime.now()
        reg_session = RegistrationSession(
            semester_id=semester.id,
            allowed_cohorts=["QH-2020-I/CQ", "K65"],
            start_time=now - timedelta(days=1), # Bắt đầu hôm qua
            end_time=now + timedelta(days=7), # Kết thúc tuần sau
            is_cancelled=False
        )
        session.add(reg_session)

        # 5. Tạo Courses & Classes & Schedules
        course_data = [
            ("INT3306", "Kiến trúc phần mềm", 3, 30),
            ("INT3110", "Phân tích thiết kế hệ thống", 3, 50),
            ("INT3202", "Hệ quản trị CSDL", 3, 2), # Rất ít slot để test overselling
            ("INT2042", "Mạng máy tính", 3, 40),
            ("INT2039", "An toàn bảo mật hệ thống thông tin", 3, 40),
            ("INT3404", "Xử lý ảnh", 3, 30),
            ("INT3111", "Quản lý dự án phần mềm", 3, 35),
            ("MAT1092", "Đại số tuyến tính", 3, 100),
            ("PHY1039", "Vật lý đại cương", 3, 100),
            ("PHI1002", "Triết học Mác Lênin", 3, 120),
            ("INT3414", "Học máy", 3, 40),
            ("INT3301", "Kiểm thử phần mềm", 3, 35),
            ("PES1001", "Bóng đá 1", 1, 30, CourseTypeEnum.physical_education),
            ("PES1002", "Bóng chuyền 1", 1, 30, CourseTypeEnum.physical_education)
        ]

        # Schedule slots (day, start, end)
        schedule_slots = [
            (2, 1, 3), (2, 4, 6), (2, 7, 9), (2, 10, 12),
            (3, 1, 3), (3, 4, 6), (3, 7, 9), (3, 10, 12),
            (4, 1, 3), (4, 4, 6), (4, 7, 9), (4, 10, 12),
            (5, 1, 3), (5, 4, 6), (5, 7, 9), (5, 10, 12),
            (6, 1, 3), (6, 4, 6), (6, 7, 9), (6, 10, 12),
            (7, 1, 3), (7, 4, 6),
        ]
        
        rooms = ["301-G2", "302-G2", "303-G2", "401-G2", "402-G2", "201-G3", "202-G3"]
        lecturers = ["Nguyễn Văn A", "Trần Thị B", "Lê Văn C", "Phạm Thị D", "Hoàng Văn E"]

        slot_idx = 0
        for data in course_data:
            c_code = data[0]
            c_name = data[1]
            credits = data[2]
            max_cap = data[3]
            c_type = data[4] if len(data) > 4 else CourseTypeEnum.normal

            course = Course(course_code=c_code, name=c_name, credits=credits, course_type=c_type)
            session.add(course)
            await session.flush()

            # Create 1-2 classes per course
            num_classes = random.randint(1, 2)
            for i in range(num_classes):
                c_class = CourseClass(
                    class_code=f"{c_code}_{i+1}",
                    course_id=course.id,
                    semester_id=semester.id,
                    room=random.choice(rooms),
                    lecturer=random.choice(lecturers),
                    max_capacity=max_cap,
                    current_capacity=0
                )
                session.add(c_class)
                await session.flush()

                # Assign a schedule
                day, start, end = schedule_slots[slot_idx % len(schedule_slots)]
                slot_idx += 1

                schedule = ClassSchedule(
                    course_class_id=c_class.id,
                    day_of_week=day,
                    start_period=start,
                    end_period=end
                )
                session.add(schedule)

        # Hoàn tất
        await session.commit()
        print("Seed Data thành công!")
        print("Admin: admin@vnu.edu.vn | Pass: dummy_password")
        print("Student: 20020000 | Pass: dummy_password")

if __name__ == "__main__":
    asyncio.run(seed_data())
