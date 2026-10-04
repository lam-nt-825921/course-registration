'use client';

import { useState } from 'react';
import { useLogin } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { AuthResponse } from '../auth';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const loginMutation = useLogin();
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    console.log('>Loading<');

    loginMutation.mutate(
      { email, password },
      {
        onSuccess: (data: AuthResponse) => {
          if (data?.token) {
            localStorage.setItem('token', data.token);
          }
          router.push('/courses');
        },
        onError: (error: any) => {
          const apiError = error.response?.data?.message || error.message;
          setErrorMessage(apiError || 'Sai thông tin');
        },
      }
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md border border-gray-200">
        <h2 className="text-2xl font-bold text-center text-emerald-800 mb-6">Đăng Nhập</h2>

        {errorMessage && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 text-sm rounded-lg border border-red-300">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email VNU
            </label>
            <input
              id="email"
              type="email"
              required
              placeholder="example@vnu.edu.vn"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none text-black"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Mật khẩu
            </label>
            <input
              id="pasword"
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none text-black"
            />
          </div>

          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="w-full py-2.5 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 transition disabled:opacity-50"
          >
            {loginMutation.isPending ? 'Đang xử lý...' : 'Đăng nhập'}
          </button>
        </form>
      </div>
    </div>
  );
}
