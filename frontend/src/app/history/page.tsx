'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/useAuthStore';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

type ClassSchedule = {
  day_of_week: number;
  start_period: number;
  end_period: number;
};

type CourseClass = {
  id: string; // UUID
  class_code: string;
  course_code: string;
  credits: number;
  course_type: string;
  max_capacity: number;
  current_capacity: number;
  schedules: ClassSchedule[];
};

type EnrollmentHistory = {
  semester_code: string;
  course_classes: CourseClass[];
};

const API_URL = 'http://localhost:8000';

const fetchEnrollmentHistory = async (): Promise<EnrollmentHistory[]> => {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${API_URL}/api/courses/enrollments/history`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error('Không thể tải lịch sử đăng ký.');
  }
  return response.json();
};

export default function HistoryPage() {
  const router = useRouter();
  const { studentId, token, logout } = useAuthStore();

  useEffect(() => {
    if (!studentId || !token) {
      router.push('/login');
    }
  }, [studentId, token, router]);

  const {
    data: history = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['enrollment-history'],
    queryFn: fetchEnrollmentHistory,
    retry: 1,
    enabled: !!studentId && !!token,
  });

  if (!studentId || !token) return null;

  return (
    <main className="min-h-screen bg-zinc-100 px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-zinc-900">Lịch sử đăng ký học</h1>
            <p className="mt-2 text-zinc-600">
              Sinh viên: <strong>{studentId}</strong>
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-sm font-medium text-zinc-700 hover:text-zinc-900 transition"
            >
              Về trang chủ
            </Link>
            <button
              onClick={logout}
              className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition"
            >
              Đăng xuất
            </button>
          </div>
        </div>

        {isError && (
          <div className="mb-6 rounded-lg bg-red-50 p-4 text-red-600 border border-red-200">
            Không thể tải lịch sử đăng ký. Vui lòng thử lại sau.
          </div>
        )}

        <section className="space-y-6">
          {isLoading ? (
            <div className="rounded-xl bg-white p-8 text-center text-zinc-500 shadow-sm">
              Đang tải lịch sử đăng ký...
            </div>
          ) : history.length === 0 ? (
            <div className="rounded-xl bg-white p-8 text-center text-zinc-500 shadow-sm">
              Chưa có dữ liệu lịch sử đăng ký.
            </div>
          ) : (
            history.map((semester) => (
              <div key={semester.semester_code} className="rounded-xl bg-white shadow-sm overflow-hidden">
                <div className="border-b border-zinc-200 bg-zinc-50 px-6 py-4">
                  <h2 className="text-lg font-semibold text-zinc-900">Kỳ học: {semester.semester_code}</h2>
                </div>
                <div className="divide-y divide-zinc-200">
                  {semester.course_classes.map((course) => {
                    const scheduleText = course.schedules.length > 0 
                      ? course.schedules.map(s => `T${s.day_of_week} (${s.start_period}-${s.end_period})`).join(', ')
                      : 'Chưa xếp lịch';
                    return (
                      <div key={course.id} className="p-6 flex flex-col gap-2">
                        <div className="flex items-center gap-3">
                          <h3 className="font-semibold text-zinc-900">{course.course_code} - {course.class_code}</h3>
                          <span className="rounded-full bg-zinc-100 border border-zinc-200 px-3 py-1 text-xs text-zinc-600 font-medium">
                            {course.credits} tín chỉ
                          </span>
                        </div>
                        <p className="text-sm text-zinc-600">
                          <span className="font-medium">Lịch học:</span> {scheduleText}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </section>
      </div>
    </main>
  );
}
