# Project Architecture Blueprint: Hệ thống Đăng ký Học phần

## 1. Executive Summary & Tech Stack Decisions

Dự án Hệ thống Đăng ký Học phần được thiết kế dựa trên các tiêu chuẩn hiện đại nhất của Frontend để đảm bảo hiệu suất, khả năng mở rộng, chất lượng code, và trải nghiệm người dùng tối ưu.

| Category | Selected Technology | Technical Justification |
| :--- | :--- | :--- |
| **Runtime Engine** | **Next.js App Router** | Hỗ trợ SSR/SSG/ISR tối ưu cho tốc độ tải trang ban đầu và SEO/GEO. Cấu trúc Routing hiện đại. |
| **Package Manager** | **pnpm (Standalone)** | Hiệu năng cài đặt siêu tốc, chống phantom dependencies, tiết kiệm dung lượng đĩa cứng. Dễ dàng tách biệt frontend/backend. |
| **UI System & Styling** | **Tailwind CSS v4 + shadcn/ui + Lucide** | Tailwind giúp style nhanh chóng không viết CSS dư thừa; shadcn/ui cho phép copy-paste component linh hoạt, dễ customize; Lucide gọn nhẹ, đồng nhất. |
| **State Management** | **TanStack Query v5 + Zustand** | TanStack Query lo fetching/caching/polling (cực kỳ quan trọng khi user liên tục tải lại danh sách lớp học); Zustand quản lý Global State (Auth, Theme) một cách gọn nhẹ. |
| **Data Contract** | **OpenAPI TS + Zod + Axios** | Tự động sinh TypeScript interface từ Swagger của FastAPI. Đảm bảo Frontend luôn đồng bộ với Backend (Single Source of Truth). Zod validate form mạnh mẽ. |
| **Quality & Testing** | **ESLint 9 + Prettier + Vitest + Playwright + Husky** | Bộ công cụ kiểm thử công nghiệp. Chặn code lỗi/xấu từ lúc commit. Test Unit siêu nhanh (Vitest) và E2E toàn diện (Playwright). |
| **SEO & A11y** | **Next Metadata + JSON-LD + WCAG 2.1 AA** | Cấu trúc chuẩn tiếp cận, dễ dàng tương tác qua bàn phím. Tối ưu thẻ meta. |

---

## 2. Directory Structure (Feature-First Screaming Architecture)

Cấu trúc thư mục ưu tiên nhóm theo tính năng (Feature-based), giúp hệ thống dễ dàng mở rộng khi nghiệp vụ Đăng ký học phần phình to.

```text
frontend/
├── src/
│   ├── app/                      # Next.js App Router (Pages, Layouts, Error Boundaries)
│   │   ├── (auth)/               # Route nhóm: Login, Register
│   │   ├── courses/              # Trang xem danh sách học phần
│   │   ├── registration/         # Trang thao tác đăng ký
│   │   ├── layout.tsx            # Root Layout
│   │   └── error.tsx             # Root Error Boundary
│   │
│   ├── features/                 # Các tính năng nghiệp vụ cốt lõi (Screaming Architecture)
│   │   ├── auth/                 # Tính năng Xác thực
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── stores/           # Zustand store cho Auth
│   │   │   └── api/
│   │   │
│   │   └── course-registration/  # Tính năng Đăng ký môn
│   │       ├── components/       # CourseCard, RegistrationTable...
│   │       ├── hooks/            # useRegisterCourse (TanStack Mutation)
│   │       └── api/              # Gọi Axios
│   │
│   ├── components/               # Components dùng chung toàn hệ thống (shadcn/ui)
│   │   ├── ui/                   # Button, Input, Dialog (do shadcn sinh ra)
│   │   └── layouts/              # Header, Footer, Sidebar
│   │
│   ├── lib/                      # Tiện ích, cấu hình thư viện
│   │   ├── axios.ts              # Cấu hình Axios Client & Interceptors
│   │   ├── query-client.ts       # Cấu hình TanStack Query
│   │   └── utils.ts              # cn() (Tailwind merge), formatter...
│   │
│   ├── api/                      # Data Contract
│   │   └── schema/               # Chứa các interface/type gen tự động từ OpenAPI
│   │
│   ├── hooks/                    # Custom hooks chung (useDebounce, useWindowSize...)
│   ├── styles/                   # globals.css
│   └── types/                    # Các type dùng chung (không liên quan API)
│
├── .husky/                       # Pre-commit hooks
├── tests/                        # Playwright E2E Tests
└── vitest.config.ts              # Cấu hình Vitest
```

---

## 3. Data Flow Architecture

Luồng dữ liệu được thiết kế theo hướng an toàn kiểu dữ liệu (Type-safe) từ Backend tới tận UI Component.

```mermaid
flowchart TD
    A[FastAPI Backend] -->|Auto-generates| B(OpenAPI / Swagger JSON)
    B -->|openapi-ts| C[Frontend API Schema `@/api/schema`]
    
    D[Axios Interceptor] -->|Gắn JWT Token & Catch 401| E{API Request}
    E -->|Gửi| A
    A -->|Trả về JSON| E
    
    E --> F[TanStack Query Hook]
    F -->|Cache, Auto-retry, Deduping| G[UI Component]
    
    C -.->|Ép kiểu (Type Inference)| F
    C -.->|Validate| H[Zod Form Schema]
    H -->|React Hook Form| G
```

---

## 4. Coding Conventions & Absolute Rules

Đây là các quy định "bất di bất dịch" (Absolute Rules) áp dụng cho mọi đoạn code trong dự án:

1. **KHÔNG tự chế Local Types cho API Data:** Bắt buộc sử dụng interfaces được sinh ra từ `@/api/schema` (OpenAPI). Nếu Backend đổi schema, Frontend phải báo lỗi type ngay lúc build.
2. **Bảo vệ toàn diện bằng Error Boundary:** Mọi route và tính năng lớn đều phải được bọc trong Error Boundary (`error.tsx` của Next.js hoặc `<ErrorBoundary>` custom) để tránh sập toàn bộ ứng dụng khi 1 component bị lỗi.
3. **Phòng chống XSS tuyệt đối:** Bất kỳ dữ liệu động nào có chứa HTML (như thông báo từ hệ thống, mô tả môn học rich-text) ĐỀU PHẢI được sanitize bằng `DOMPurify` trước khi render ra màn hình.
4. **Bảo mật PII & Secret:** 
   - KHÔNG BAO GIỜ được phép `console.log` token, mật khẩu, hay thông tin cá nhân (PII) ra browser console.
   - Các biến môi trường nhạy cảm phải bắt buộc có prefix hợp lý và không được lộ ở client (trừ `NEXT_PUBLIC_`).
