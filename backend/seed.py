import asyncio
import os
import sys
import random

# Add path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select

from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.database.models import (
    Course, CourseTypeEnum, User, RoleEnum, Student, 
    Semester, RegistrationSession, CourseClass, ClassSchedule,
    CoursePrerequisite, AcademicTranscript, TranscriptStatusEnum
)
from src.application.security.auth import get_password_hash

async def clear_database(session: AsyncSession):
    print("Xóa dữ liệu cũ...")
    await session.execute(text("TRUNCATE TABLE users, majors, students, major_courses, courses, course_prerequisites, semesters, registration_sessions, course_classes, class_schedules, enrollments, audit_logs, academic_transcripts RESTART IDENTITY CASCADE;"))
    await session.commit()

async def seed_data():
    async with AsyncSessionLocal() as session:
        await clear_database(session)

        print("Đang thêm Seed Data cho Hệ thống...")
        
        # Mật khẩu chung là "1" theo yêu cầu
        hashed_pw = get_password_hash("1")
        
        # 1. Tạo Admin
        admin_user = User(
            email="admin@vnu.edu.vn",
            password_hash=hashed_pw,
            role=RoleEnum.admin
        )
        session.add(admin_user)
        
        from src.infrastructure.database.models import Major, MajorCourse

        major_names = ["CNTT", "Khoa học máy tính", "Hệ thống thông tin", "Mạng máy tính", "Kỹ thuật phần mềm"]
        major_objs = {}
        for m_name in major_names:
            m = Major(name=m_name)
            session.add(m)
            await session.flush()
            major_objs[m_name] = m

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
            cohort="QH-2020-I/CQ",
            major_id=major_objs["Kỹ thuật phần mềm"].id
        )
        session.add(student_profile)

        # Tạo thêm 500 sinh viên ngẫu nhiên
        student_objs = [student_profile]
        for i in range(1, 501):
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
                cohort="QH-2020-I/CQ",
                major_id=major_objs[random.choice(major_names)].id
            )
            session.add(s_profile)
            student_objs.append(s_profile)

        # 3. Tạo Semester
        semester = Semester(
            code="20241",
            is_active=True
        )
        session.add(semester)
        await session.flush()
        
        from datetime import datetime, timedelta
        # 4. Tạo Registration Session (phiên đăng ký)
        now = datetime.now()
        reg_session = RegistrationSession(
            semester_id=semester.id,
            allowed_cohorts=["QH-2020-I/CQ", "K65", "QH-2021-I/CQ", "QH-2022-I/CQ"],
            start_time=now - timedelta(days=1), # Bắt đầu hôm qua
            end_time=now + timedelta(days=7), # Kết thúc tuần sau
            is_cancelled=False
        )
        session.add(reg_session)

        # 5. Tạo Courses (có chuyên ngành)
        course_data = [
            # Mã, Tên, Tín chỉ, Sĩ số, Loại, Chuyên ngành
            ("INT1000", "Tin học cơ sở", 3, 100, CourseTypeEnum.normal, None), # Đại cương, không chuyên ngành
            ("INT2000", "Lập trình C++", 3, 80, CourseTypeEnum.normal, None),
            ("INT2001", "Cấu trúc dữ liệu và giải thuật", 3, 80, CourseTypeEnum.normal, None),
            
            # CNTT / Khoa học máy tính
            ("INT3114", "Toán rời rạc", 3, 50, CourseTypeEnum.normal, "Khoa học máy tính"),
            ("INT3404", "Xử lý ảnh", 3, 40, CourseTypeEnum.normal, "Khoa học máy tính"),
            ("INT3414", "Học máy", 3, 40, CourseTypeEnum.normal, "Khoa học máy tính"),
            
            # Kỹ thuật phần mềm
            ("INT3306", "Kiến trúc phần mềm", 3, 30, CourseTypeEnum.normal, "Kỹ thuật phần mềm"),
            ("INT3110", "Phân tích thiết kế hệ thống", 3, 50, CourseTypeEnum.normal, "Kỹ thuật phần mềm"),
            ("INT3301", "Kiểm thử phần mềm", 3, 35, CourseTypeEnum.normal, "Kỹ thuật phần mềm"),
            ("INT3111", "Quản lý dự án phần mềm", 3, 35, CourseTypeEnum.normal, "Kỹ thuật phần mềm"),
            
            # Hệ thống / Mạng
            ("INT3202", "Hệ quản trị CSDL", 3, 2, CourseTypeEnum.normal, "Hệ thống thông tin"),
            ("INT2042", "Mạng máy tính", 3, 40, CourseTypeEnum.normal, "Mạng máy tính"),
            ("INT2039", "An toàn bảo mật hệ thống", 3, 40, CourseTypeEnum.normal, "Mạng máy tính"),
            
            # Các môn khác
            ("MAT1092", "Đại số tuyến tính", 3, 100, CourseTypeEnum.normal, None),
            ("PHY1039", "Vật lý đại cương", 3, 100, CourseTypeEnum.normal, None),
            ("PHI1002", "Triết học Mác Lênin", 3, 120, CourseTypeEnum.normal, None),
            ("PES1001", "Bóng đá 1", 1, 30, CourseTypeEnum.physical_education, None),
            ("PES1002", "Bóng chuyền 1", 1, 30, CourseTypeEnum.physical_education, None)
        ]

        courses = {}
        # Lưu sĩ số max
        course_max_cap = {}
        for data in course_data:
            course = Course(
                course_code=data[0], 
                name=data[1], 
                credits=data[2], 
                course_type=data[4]
            )
            course_max_cap[data[0]] = data[3]
            session.add(course)
            await session.flush()
            courses[data[0]] = course
            
            # Mapping MajorCourse
            c_major = data[5]
            if c_major:
                mc = MajorCourse(major_id=major_objs[c_major].id, course_id=course.id)
                session.add(mc)
                await session.flush()

        # 6. Thêm môn tiên quyết
        prereqs = [
            ("INT2000", "INT1000"), # Lập trình C++ yêu cầu Tin học cơ sở
            ("INT2001", "INT2000"), # CTDL & GT yêu cầu C++
            ("INT3306", "INT3110"), # Kiến trúc PM yêu cầu Phân tích TKHT
            ("INT3110", "INT2001"), # PT TKHT yêu cầu CTDL&GT
            ("INT3414", "MAT1092"), # Học máy yêu cầu ĐSTT
        ]
        for course_code, prereq_code in prereqs:
            c = courses[course_code]
            p = courses[prereq_code]
            session.add(CoursePrerequisite(course_id=c.id, prereq_id=p.id))

        # 7. Thêm lịch sử học tập (AcademicTranscript) cho sinh viên
        # Để có trường hợp: đã học (passed), học lại (failed)
        print("Tạo lịch sử học tập...")
        for student in student_objs:
            # Randomly pass some base courses so they can take advanced courses
            if random.random() > 0.2:
                # 80% pass INT1000
                session.add(AcademicTranscript(student_id=student.user_id, course_id=courses["INT1000"].id, status=TranscriptStatusEnum.passed))
                
                if random.random() > 0.3:
                    # 70% pass INT2000
                    session.add(AcademicTranscript(student_id=student.user_id, course_id=courses["INT2000"].id, status=TranscriptStatusEnum.passed))
                    
                    if random.random() > 0.5:
                        # 50% fail INT2001 (need retake)
                        session.add(AcademicTranscript(student_id=student.user_id, course_id=courses["INT2001"].id, status=TranscriptStatusEnum.failed))
                    else:
                        # 50% pass INT2001
                        session.add(AcademicTranscript(student_id=student.user_id, course_id=courses["INT2001"].id, status=TranscriptStatusEnum.passed))
                        
                        # Pass some major courses if matched major
                        if student.major_id == major_objs["Kỹ thuật phần mềm"].id:
                            session.add(AcademicTranscript(student_id=student.user_id, course_id=courses["INT3110"].id, status=TranscriptStatusEnum.passed))

        # 8. Tạo Classes & Schedules
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
        for c_code, course in courses.items():
            max_cap = course_max_cap[c_code]
            num_classes = random.randint(1, 3)
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
        print("Admin: admin@vnu.edu.vn | Pass: 1")
        print("Student: 20020000 (và từ 20020001 đến 20020500) | Pass: 1")

if __name__ == "__main__":
    asyncio.run(seed_data())
