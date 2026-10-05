'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/useAuthStore';
import Link from 'next/link';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { role, logout, studentId } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted) {
      if (!role) {
        router.push('/login');
      } else if (role !== 'admin') {
        router.push('/');
      }
    }
  }, [role, router, mounted]);

  if (!mounted || role !== 'admin') return null;

  return (
    <main className="min-h-screen bg-zinc-100">
      <header className="bg-white border-b border-zinc-200 px-6 py-4 shadow-sm">
        <div className="mx-auto max-w-6xl flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900">Admin Dashboard</h1>
            <p className="text-sm text-zinc-600">
              Quản trị viên: <strong>{studentId}</strong>
            </p>
          </div>
          <button
            onClick={logout}
            className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition"
          >
            Đăng xuất
          </button>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-6 py-8">
        <nav className="mb-6 flex space-x-2 border-b border-zinc-200">
          <Link
            href="/admin/sessions"
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              pathname.startsWith('/admin/sessions')
                ? 'bg-zinc-200 text-zinc-900 border-b-2 border-zinc-900'
                : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
            }`}
          >
            Quản lý Phiên Đăng ký
          </Link>
          <Link
            href="/admin/logs"
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              pathname.startsWith('/admin/logs')
                ? 'bg-zinc-200 text-zinc-900 border-b-2 border-zinc-900'
                : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
            }`}
          >
            Audit Logs
          </Link>
        </nav>
        {children}
      </div>
    </main>
  );
}
