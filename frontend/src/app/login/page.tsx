'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/useAuthStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const loginApi = async ({ studentId, password }: { studentId: string; password: string }) => {
  const formData = new URLSearchParams();
  formData.append('username', studentId);
  formData.append('password', password);

  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Đăng nhập thất bại');
  }

  return response.json();
};

export default function LoginPage() {
  const [studentId, setStudentId] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();
  const login = useAuthStore((state) => state.login);

  const mutation = useMutation({
    mutationFn: loginApi,
    onSuccess: (data) => {
      toast.success('Đăng nhập thành công');
      login(studentId, data.access_token || 'dummy_token');
      router.push('/');
    },
    onError: (error: Error) => {
      toast.error(error.message);
      if (error.message === 'Failed to fetch') {
        toast.info('Đăng nhập với chế độ Mock (API chưa có)');
        login(studentId, 'mock_token');
        router.push('/');
      }
    },
  });

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!studentId.trim()) {
      toast.warning('Vui lòng nhập mã sinh viên');
      return;
    }
    if (!password.trim()) {
      toast.warning('Vui lòng nhập mật khẩu');
      return;
    }
    mutation.mutate({ studentId, password });
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-100 p-6">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="mb-2 text-2xl font-bold text-zinc-900">Đăng nhập</h1>
        <p className="mb-6 text-sm text-zinc-600">
          Nhập mã sinh viên và mật khẩu để truy cập hệ thống.
        </p>

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label htmlFor="studentId" className="mb-2 block text-sm font-medium text-zinc-700">
              Mã sinh viên
            </label>
            <input
              id="studentId"
              type="text"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="VD: 20020000"
              className="w-full rounded-lg border border-zinc-300 px-4 py-3 outline-none transition focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-2 block text-sm font-medium text-zinc-700">
              Mật khẩu
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Nhập mật khẩu"
              className="w-full rounded-lg border border-zinc-300 px-4 py-3 outline-none transition focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200"
            />
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="mt-2 w-full rounded-lg bg-zinc-900 py-3 font-medium text-white transition hover:bg-zinc-800 disabled:bg-zinc-400"
          >
            {mutation.isPending ? 'Đang xử lý...' : 'Đăng nhập'}
          </button>
        </form>
      </div>
    </main>
  );
}
