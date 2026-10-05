import { create } from 'zustand';

interface AuthState {
  studentId: string | null;
  token: string | null;
  login: (studentId: string, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  studentId: null,
  token: null,
  login: (studentId, token) => set({ studentId, token }),
  logout: () => set({ studentId: null, token: null }),
}));
