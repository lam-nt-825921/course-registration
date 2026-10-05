# Hệ Thống Đăng Ký Học Phần (Course Registration System)

Dự án này được xây dựng nhằm mục đích thực hành và thiết kế Kiến trúc Phần mềm, đáp ứng các yêu cầu đánh giá kiến trúc phần mềm từ cơ bản (Pha 1) đến tối ưu hóa nâng cao (Pha 2).

> **Lưu ý**: Các tài liệu thiết kế hệ thống, lộ trình, và quy định lập trình chi tiết được lưu trong thư mục `docs/`.
> - [Kiến trúc hệ thống (Architecture)](./docs/architecture.md)
> - [Hướng dẫn lập trình và Lộ trình (Development Guide)](./docs/development_guide.md)

---

## 🚀 Hướng dẫn cài đặt và chạy hệ thống (Local Development)

Sau khi pull repository từ Github về, hãy làm theo các bước dưới đây để khởi chạy toàn bộ hệ thống.

### 1. Khởi động Cơ sở dữ liệu (PostgreSQL & Redis)
Yêu cầu: Máy bạn đã cài đặt [Docker](https://docs.docker.com/get-docker/) và Docker Compose.

Mở terminal tại thư mục gốc của dự án (`course-registration`) và chạy lệnh:
```bash
docker compose up -d
```
Lệnh này sẽ khởi động PostgreSQL (chứa dữ liệu) ở cổng `5432` và Redis (dùng cho Rate Limiter/Cache) ở cổng `6379`.

### 2. Khởi chạy Backend (FastAPI)
Yêu cầu: Máy bạn đã cài đặt Python 3.10+.

Mở một tab terminal mới và chạy các lệnh sau:
```bash
cd backend
python -m venv venv

# Kích hoạt môi trường ảo (Virtual Environment)
# Trên Linux/MacOS:
source venv/bin/activate
# Trên Windows (Git Bash/PowerShell):
# source venv/Scripts/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy server FastAPI
uvicorn main:app --reload
```
API Backend sẽ chạy tại: **http://localhost:8000**
Bạn có thể xem toàn bộ tài liệu API (Swagger UI) tại: **http://localhost:8000/docs**

### 3. Khởi chạy Frontend (Next.js)
Yêu cầu: Máy bạn đã cài đặt Node.js 18+ và [pnpm](https://pnpm.io/installation).

Mở một tab terminal mới và chạy:
```bash
# Cài đặt dependencies và kích hoạt Git Hooks
pnpm install

# Đi vào thư mục frontend và chạy app
cd frontend
pnpm run dev
```
Frontend Web sẽ chạy tại: **http://localhost:3000**

---
🎉 **Thế là xong! Bạn đã có thể truy cập http://localhost:3000 để sử dụng hệ thống.**
