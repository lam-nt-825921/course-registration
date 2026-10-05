import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface AuthState {
  studentId: string | null;
  role: string | null;
  token: string | null;
  login: (studentId: string, role: string, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      studentId: null,
      role: null,
      token: null,
      login: (studentId, role, token) => set({ studentId, role, token }),
      logout: () => set({ studentId: null, role: null, token: null }),
    }),
    {
      name: 'auth-storage', // name of the item in the storage (must be unique)
      storage: createJSONStorage(() => localStorage),
    }
  )
);
