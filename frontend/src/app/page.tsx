'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/useAuthStore';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

type Course = {
  id: number;
  code: string;
  name: string;
  credits: number;
  max_slots: number;
  registered_slots: number;
};

const API_URL = 'http://localhost:8000';

const fetchCourses = async (): Promise<Course[]> => {
  const response = await fetch(`${API_URL}/api/courses/`);
  if (!response.ok) {
    throw new Error('Không thể tải danh sách học phần.');
  }
  return response.json();
};

const registerCourse = async ({ courseId, studentId }: { courseId: number; studentId: string }) => {
  const response = await fetch(
    `${API_URL}/api/courses/${courseId}/register?student_id=${encodeURIComponent(studentId)}`,
    {
      method: 'POST',
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Đăng ký học phần thất bại.');
  }
  return data;
};

export default function Home() {
  const router = useRouter();
  const { studentId, logout } = useAuthStore();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!studentId) {
      router.push('/login');
    }
  }, [studentId, router]);

  const {
    data: courses = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['courses'],
    queryFn: fetchCourses,
    retry: 1,
    enabled: !!studentId,
  });

  const mutation = useMutation({
    mutationFn: registerCourse,
    onSuccess: (data) => {
      toast.success(data.message || 'Đăng ký học phần thành công.');
      queryClient.invalidateQueries({ queryKey: ['courses'] });
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  if (isError) {
    toast.error('Không thể kết nối đến máy chủ. Vui lòng kiểm tra Backend đang chạy.', {
      id: 'fetch-error',
    });
  }

  const handleRegister = (courseId: number) => {
    if (!studentId) return;
    mutation.mutate({ courseId, studentId });
  };

  if (!studentId) return null; // Prevent hydration errors during redirect

  return (
    <main className="min-h-screen bg-zinc-100 px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-zinc-900">Đăng ký học phần</h1>
            <p className="mt-2 text-zinc-600">
              Xin chào, sinh viên <strong>{studentId}</strong>
            </p>
          </div>
          <button
            onClick={logout}
            className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Đăng xuất
          </button>
        </div>

        <section className="rounded-xl bg-white shadow-sm">
          <div className="border-b border-zinc-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-zinc-900">Danh sách học phần</h2>
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-zinc-500">Đang tải danh sách học phần...</div>
          ) : courses.length === 0 ? (
            <div className="p-8 text-center text-zinc-500">Hiện chưa có học phần nào.</div>
          ) : (
            <div className="divide-y divide-zinc-200">
              {courses.map((course) => {
                const isFull = course.registered_slots >= course.max_slots;
                const isRegistering =
                  mutation.isPending && mutation.variables?.courseId === course.id;

                return (
                  <div
                    key={course.id}
                    className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-zinc-900">{course.code}</h3>
                        <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-600">
                          {course.credits} tín chỉ
                        </span>
                      </div>
                      <p className="mt-1 text-zinc-700">{course.name}</p>
                      <p className="mt-2 text-sm text-zinc-500">
                        Đã đăng ký: {course.registered_slots} / {course.max_slots}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRegister(course.id)}
                      disabled={isFull || isRegistering}
                      className="rounded-lg bg-zinc-900 px-5 py-3 font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                    >
                      {isRegistering ? 'Đang đăng ký...' : isFull ? 'Đã đầy' : 'Đăng ký'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
