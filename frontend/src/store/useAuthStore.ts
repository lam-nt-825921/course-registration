import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface AuthState {
  studentId: string | null;
  role: string | null;
  token: string | null;
  login: (studentId: string, role: string, token: string) => void;
  /** Đăng xuất chủ động: báo backend bắt đầu 20 phút chờ (chỉ sinh viên), rồi xóa phiên local. */
  logout: () => void;
  /** Chỉ xóa phiên ở trình duyệt, không gọi API (dùng khi phiên đã hết hạn / bị 401). */
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      studentId: null,
      role: null,
      token: null,
      login: (studentId, role, token) => set({ studentId, role, token }),
      logout: () => {
        const { token, role } = get();
        if (token && role === 'student' && token !== 'mock_token') {
          try {
            // Fire-and-forget: UI không phải chờ backend
            Promise.resolve(
              fetch(`${API_URL}/api/auth/logout`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                keepalive: true,
              })
            ).catch(() => { });
          } catch {
            // bỏ qua lỗi mạng khi đăng xuất
          }
        }
        set({ studentId: null, role: null, token: null });
      },
      clearAuth: () => set({ studentId: null, role: null, token: null }),
    }),
    {
      name: 'auth-storage', // name of the item in the storage (must be unique)
      storage: createJSONStorage(() => localStorage),
    }
  )
);
