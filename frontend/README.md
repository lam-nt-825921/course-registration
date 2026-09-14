# Frontend: Hệ Thống Đăng Ký Học Phần

Phân hệ Frontend được xây dựng theo chuẩn công nghiệp hiện đại, tập trung vào trải nghiệm người dùng, hiệu năng tải trang và chất lượng mã nguồn.

## 🛠 Tech Stack

- **Framework**: [Next.js 15+ (App Router)](https://nextjs.org/) + React 19
- **Package Manager**: pnpm
- **Styling**: Tailwind CSS v4
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/) + Radix UI + Lucide React
- **State Management**: 
  - *Server State*: TanStack Query v5 (Quản lý fetching, caching, deduplication)
  - *Client State*: Zustand (Quản lý Theme, Auth state...)
- **Data Contract**: OpenAPI TS Generator + Zod (Validation)
- **Quality Gates**: ESLint 9 (Flat config), Prettier, Vitest, Playwright, Husky & lint-staged

## 📂 Cấu trúc thư mục (Feature-First)

Cấu trúc mã nguồn tuân thủ triết lý **Screaming Architecture**, phân chia theo tính năng nghiệp vụ thay vì loại file.

```text
frontend/
├── src/
│   ├── app/                      # Next.js Routing, Layouts, Pages
│   ├── features/                 # Logic nghiệp vụ độc lập (Auth, Courses...)
│   │   ├── auth/                 # Tính năng đăng nhập/đăng ký
│   │   └── registration/         # Tính năng chọn và đăng ký lớp
│   ├── components/               # UI Component dùng chung (shadcn/ui)
│   ├── lib/                      # Tiện ích chung, config Axios, Utils
│   ├── api/                      # Chứa type sinh tự động từ Swagger
│   └── styles/                   # Global CSS
└── package.json                  # Cấu hình project
```

## 🚀 Hướng dẫn cài đặt & Khởi chạy

**Yêu cầu hệ thống:** Node.js 20+ và `pnpm`

1. Cài đặt dependencies:
   ```bash
   pnpm install
   ```

2. Chạy môi trường phát triển (Development mode):
   ```bash
   pnpm run dev
   ```
   *Truy cập [http://localhost:3000](http://localhost:3000)*

3. Build production:
   ```bash
   pnpm run build
   pnpm run start
   ```

## 🛑 Quy tắc Code (Tuyệt đối)

1. **Type-Safety**: Không viết `any`. Không tự chế interface cho API. Mọi dữ liệu trả về từ backend phải dùng type sinh tự động từ OpenAPI.
2. **Validation**: Mọi Form Data phải được xác thực bằng `Zod` trước khi gửi lên API.
3. **Security**: Sử dụng `DOMPurify` nếu bắt buộc phải dùng `dangerouslySetInnerHTML`.
