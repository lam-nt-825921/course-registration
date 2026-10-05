import asyncio
import os
import sys

# Add path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.database.models import Course, CourseTypeEnum

async def seed_data():
    async with AsyncSessionLocal() as session:
        # Check if we already have data
        result = await session.execute(select(Course))
        if result.scalars().first() is not None:
            print("Dữ liệu đã tồn tại. Bỏ qua seeding.")
            return

        print("Đang thêm Seed Data cho môn học...")
        courses = [
            Course(course_code="INT3306", credits=3, course_type=CourseTypeEnum.normal),
            Course(course_code="INT3110", credits=3, course_type=CourseTypeEnum.normal),
            Course(course_code="INT3202", credits=3, course_type=CourseTypeEnum.normal),
            Course(course_code="INT3301", credits=3, course_type=CourseTypeEnum.normal),
            Course(course_code="INT3307", credits=3, course_type=CourseTypeEnum.normal),
            Course(course_code="INT3308", credits=3, course_type=CourseTypeEnum.normal),
        ]
        
        session.add_all(courses)
        await session.commit()
        print("Seed Data thành công!")

if __name__ == "__main__":
    asyncio.run(seed_data())
