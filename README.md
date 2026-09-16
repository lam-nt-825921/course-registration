# Hệ Thống Đăng Ký Học Phần (Course Registration System)

Dự án này được xây dựng nhằm mục đích thực hành và thiết kế Kiến trúc Phần mềm, đáp ứng các yêu cầu đánh giá kiến trúc phần mềm từ cơ bản (Pha 1) đến tối ưu hóa nâng cao (Pha 2).

## 🚀 Tổng quan kiến trúc

Dự án được chia làm 2 phân hệ hoàn toàn độc lập (Standalone Architecture) để dễ dàng scale và deploy:

- **Frontend (`/frontend`)**: Xây dựng bằng **Next.js (App Router)** với giao diện Tailwind CSS + shadcn/ui. Tối ưu hóa UI/UX và cơ chế fetching dữ liệu mạnh mẽ bằng TanStack Query.
- **Backend (`/backend`)**: Xây dựng bằng **Python FastAPI**, tuân thủ nghiêm ngặt **Kiến trúc phân tầng (Layered Architecture)** và **Repository Pattern**. Tách biệt hoàn toàn tầng nghiệp vụ khỏi framework và database.

*Chi tiết về thiết kế kiến trúc, luồng dữ liệu (Data Flow) và các quyết định công nghệ (Tech Stack Decisions), vui lòng xem tại file: [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md).*

## 📂 Cấu trúc Repository

```text
course-registration/
├── frontend/                 # Source code Frontend (Next.js, React)
├── backend/                  # Source code Backend API (FastAPI, PostgreSQL)
├── PROJECT_ARCHITECTURE.md   # Tài liệu đặc tả kiến trúc SSOT
└── README.md                 # File giới thiệu dự án (bạn đang đọc)
```

## ⚙️ Kế hoạch phát triển (Lộ trình)

### Pha 1: Chức năng cơ bản (Hoàn thành)
- [x] Thiết lập cấu trúc Frontend chuẩn mực (ESLint, Prettier, Husky, Next.js).
- [x] Thiết lập cấu trúc Backend phân tầng nghiêm ngặt (API -> Domain/Use Cases -> Infrastructure).
- [ ] Implement các API cơ bản: Quản lý môn học, Đăng nhập/Xác thực (JWT), Đăng ký học phần.
- [ ] Container hóa bằng Docker (Dockerfile & docker-compose.yml).
- [ ] Kiểm thử tải cơ bản nghiệm thu trên cấu hình phần cứng cố định (Kaggle CPU).

### Pha 2: Tối ưu hóa Kiến trúc (Dự kiến)
Để giải quyết bài toán "Thundering Herd" (Lượng truy cập tăng đột biến cùng 1 thời điểm lúc mở form đăng ký), kiến trúc sẽ được nâng cấp:
1. **Caching**: Tích hợp Redis để cache danh sách môn học, giảm tải PostgreSQL.
2. **Asynchronous/Queue**: Tích hợp Message Queue (RabbitMQ / Redis PubSub) để xử lý bất đồng bộ các request ghi dữ liệu (đăng ký môn).
3. **CQRS**: Phân tách model Đọc - Ghi.

## 🛠 Hướng dẫn chạy dự án

Bạn vui lòng đọc hướng dẫn chi tiết trong từng thư mục:
- 👉 [Hướng dẫn khởi chạy Frontend](./frontend/README.md)
- 👉 [Hướng dẫn khởi chạy Backend](./backend/README.md)

## 🐶 Quy trình Quản lý Code & Git Hooks (Husky)

Dự án áp dụng mô hình **Root Husky** điều phối 2 child huskies ở `frontend` và `backend`. Điều này đảm bảo mọi dòng code được kiểm tra nghiêm ngặt trước khi commit.

### Hướng dẫn cài đặt Hooks
Chạy lệnh sau tại **thư mục gốc (root)** của dự án:
```bash
pnpm install
```
*(Lệnh này sẽ tự động kích hoạt Husky. Khi bạn commit, nó sẽ lần lượt gọi linter của cả frontend và backend).*

### Quy ước Commit (Conventional Commits)
Bắt buộc sử dụng cấu trúc: `<type>(<scope>): <subject>`
- `feat`: Thêm tính năng mới (Ví dụ: `feat(auth): thêm api đăng nhập JWT`)
- `fix`: Sửa lỗi bug (Ví dụ: `fix(course): sửa lỗi tràn UI nút đăng ký`)
- `docs`: Cập nhật tài liệu (Ví dụ: `docs: update README`)
- `refactor`: Tối ưu code không làm thay đổi logic
- `test`: Thêm/sửa Unit Test

### Quy ước Code
- **Frontend**: Tuân thủ ESLint (Flat Config) và Prettier. Không được có lỗi `any` hoặc `ts-error`.
- **Backend**: Tuân thủ PEP8, sử dụng `black` hoặc `flake8` để format code.
