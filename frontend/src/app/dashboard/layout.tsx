'use client';

import Providers from '@/lib/providers';
import { useAuthStore } from '@/lib/store/useAuthStore';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null; // Tránh flash nội dung trước khi chuyển hướng
  }

  return (
    <Providers>
      <div className="min-h-screen flex flex-col bg-slate-50">
        <header className="bg-emerald-700 text-white p-4 shadow-md flex justify-between items-center">
          <h1 className="text-xl font-bold">Đăng Ký Học VNU</h1>
          <button
            onClick={() => useAuthStore.getState().logout()}
            className="bg-emerald-800 hover:bg-emerald-900 px-3 py-1 text-sm rounded transition"
          >
            Đăng xuất
          </button>
        </header>
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">{children}</main>
      </div>
    </Providers>
  );
}
