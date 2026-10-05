# Kế hoạch phát triển và Hướng dẫn lập trình (Development Guide)

## ⚙️ Kế hoạch phát triển (Lộ trình)

### Pha 1: Chức năng cơ bản (Hoàn thành)
- [x] Thiết lập cấu trúc Frontend chuẩn mực (ESLint, Prettier, Husky, Next.js).
- [x] Thiết lập cấu trúc Backend phân tầng nghiêm ngặt (API -> Domain/Use Cases -> Infrastructure).
- [x] Implement các API cơ bản: Quản lý môn học, Đăng nhập/Xác thực (JWT), Đăng ký học phần.
- [x] Container hóa bằng Docker (docker-compose.yml cho PostgreSQL + Redis).
- [ ] Kiểm thử tải cơ bản nghiệm thu trên cấu hình phần cứng cố định (Kaggle CPU).

### Pha 2: Tối ưu hóa Kiến trúc (Dự kiến)
Để giải quyết bài toán "Thundering Herd" (Lượng truy cập tăng đột biến cùng 1 thời điểm lúc mở form đăng ký), kiến trúc sẽ được nâng cấp:
1. **Caching**: Tích hợp Redis để cache danh sách môn học, giảm tải PostgreSQL.
2. **Asynchronous/Queue**: Tích hợp Message Queue (RabbitMQ / Redis PubSub) để xử lý bất đồng bộ các request ghi dữ liệu (đăng ký môn).
3. **CQRS**: Phân tách model Đọc - Ghi.

---

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
- **DB Migrations**: Thư mục `backend/alembic/` bắt buộc phải push lên repo để quản lý schema (không push password thực tế lên file config).
