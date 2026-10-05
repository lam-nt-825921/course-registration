import os
import sys

# Thêm đường dẫn để có thể import từ app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database.session import SessionLocal, engine
from app.infrastructure.database.models import Base, CourseModel

def seed_data():
    print("Tạo các bảng (nếu chưa có)...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Kiểm tra xem đã có dữ liệu chưa
        if db.query(CourseModel).count() > 0:
            print("Dữ liệu đã tồn tại. Bỏ qua seeding.")
            return

        print("Đang thêm Seed Data cho môn học...")
        courses = [
            CourseModel(code="INT3306", name="Kiến trúc phần mềm", credits=3, max_slots=60, registered_slots=0),
            CourseModel(code="INT3110", name="Phân tích thiết kế hệ thống", credits=3, max_slots=50, registered_slots=0),
            CourseModel(code="INT3202", name="Hệ quản trị cơ sở dữ liệu", credits=3, max_slots=40, registered_slots=0),
            CourseModel(code="INT3301", name="Phát triển ứng dụng Web", credits=3, max_slots=30, registered_slots=0),
            CourseModel(code="INT3307", name="An toàn và bảo mật hệ thống thông tin", credits=3, max_slots=60, registered_slots=0),
            CourseModel(code="INT3308", name="Mạng máy tính nâng cao", credits=3, max_slots=5, registered_slots=0), # Môn này set max_slots nhỏ để dễ test Overselling
        ]
        
        db.add_all(courses)
        db.commit()
        print("Seed Data thành công!")
        
    except Exception as e:
        print(f"Lỗi khi seed data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
