# Backend API: Hệ Thống Đăng Ký Học Phần

Backend được thiết kế chặt chẽ theo **Kiến trúc phân tầng (Layered Architecture)**, tách biệt hoàn toàn giữa kỹ thuật framework và thuật toán nghiệp vụ cốt lõi. Thiết kế này giúp hệ thống sẵn sàng nâng cấp và thay đổi cơ sở hạ tầng ở Pha 2.

## 🛠 Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.0 (Triển khai Data Mapper pattern)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Authentication**: JWT (JSON Web Tokens) + Passlib (Bcrypt)

## 📂 Cấu trúc kiến trúc phân tầng

```text
backend/
├── app/
│   ├── api/                      # TẦNG 1: Giao tiếp (Routing, HTTP, Middleware)
│   │   ├── endpoints/            
│   │   └── dependencies.py       # Dependency Injection container
│   │
│   ├── use_cases/                # TẦNG 2: Business Logic / Application Services
│   │   └── course_service.py     # Nơi xử lý thuật toán đăng ký. ❌ Không chứa web/db
│   │
│   ├── domain/                   # TẦNG 3: Domain Entities & Interfaces
│   │   ├── entities/             # Các Data Class thuần túy
│   │   └── repositories/         # Các Interface bắt buộc tầng Data phải tuân thủ
│   │
│   └── infrastructure/           # TẦNG 4: Data Access / External Services
│       ├── database/             # Kết nối SQLAlchemy
│       └── repositories/         # Các SQL Implementation gọi vào Database
│
├── requirements.txt
└── main.py                       # Điểm khởi chạy FastAPI
```

## 🚀 Hướng dẫn cài đặt & Khởi chạy

**Yêu cầu hệ thống:** Python 3.11+ và Database PostgreSQL.

### 1. Cài đặt môi trường cục bộ (Local)

1. Tạo môi trường ảo (Virtual Env) và kích hoạt:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate   # Windows
   ```

2. Cài đặt các thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

3. Khởi chạy Server Development:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   *Truy cập tài liệu API (Swagger UI) tại: [http://localhost:8000/docs](http://localhost:8000/docs)*

### 2. Triển khai bằng Docker

Dự án đã có sẵn `Dockerfile`. Bạn có thể build và chạy ngay lập tức:

```bash
docker build -t course-backend .
docker run -p 8000:8000 course-backend
```

## 🛑 Quy tắc thiết kế (Design Rules)

1. **Dependency Rule**: Luồng dữ liệu (Data Flow) đi từ ngoài vào trong, nhưng Dependency đi từ trong ra ngoài (Inversion of Control).
2. Tầng `use_cases` và `domain` tuyệt đối không được phép import `fastapi` hay `sqlalchemy`.
3. Mọi truy cập vào database phải đi qua interface ở thư mục `domain/repositories`.
