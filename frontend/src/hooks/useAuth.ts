import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { LoginCredentials, AuthResponse } from '@/app/auth';
import { useAuthStore } from '@/lib/store/useAuthStore';

export function useLogin() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      if (!credentials.email.toLowerCase().endsWith('@vnu.edu.vn')) {
        throw new Error('Chỉ chấp nhận email định danh @vnu.edu.vn');
      }

      const response = await api.post<AuthResponse>('/login', credentials);
      return response.data;
    },
    onSuccess: (data: AuthResponse) => {
      setAuth(data.user, data.accessToken);
    },
  });
}
