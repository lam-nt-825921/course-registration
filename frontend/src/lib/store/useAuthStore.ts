import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User } from '@/app/auth';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      // Cập nhật thông tin User & Token sau khi Login thành công
      setAuth: (user, token) => set({ user, accessToken: token, isAuthenticated: true }),

      // Xoá thông tin khi Đăng xuất
      logout: () => set({ user: null, accessToken: null, isAuthenticated: false }),
    }),
    {
      name: 'vnu-auth-storage', // Key lưu dưới LocalStorage
      storage: createJSONStorage(() => localStorage),
    }
  )
);
