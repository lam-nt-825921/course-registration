'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/useAuthStore';
import Link from 'next/link';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

type ClassSchedule = {
  day_of_week: number;
  start_period: number;
  end_period: number;
};

type CourseClass = {
  id: string;
  class_code: string;
  course_code: string;
  credits: number;
  course_type: string;
  max_capacity: number;
  current_capacity: number;
  schedules: ClassSchedule[];
  is_valid?: boolean;
  course_name?: string;
  room?: string;
  lecturer?: string;
  note?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const fetchCourses = async (): Promise<CourseClass[]> => {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${API_URL}/api/courses/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Không thể tải danh sách học phần.');
  }
  return response.json();
};

const fetchMySchedule = async (): Promise<CourseClass[]> => {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${API_URL}/api/courses/my-schedule`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Không thể tải thời khóa biểu.');
  return response.json();
};

const registerCourse = async ({ courseClassId }: { courseClassId: string }) => {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${API_URL}/api/courses/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ course_class_id: courseClassId }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Đăng ký học phần thất bại.');
  return data;
};

const cancelRegistration = async (classId: string) => {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${API_URL}/api/courses/register/${classId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Hủy đăng ký học phần thất bại.');
  return data;
};

export default function Home() {
  const router = useRouter();
  const { studentId, token, role, logout } = useAuthStore();
  const queryClient = useQueryClient();

  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted) {
      if (!token) {
        router.push('/login');
      } else if (role === 'admin') {
        router.push('/admin');
      }
    }
  }, [token, role, router, mounted]);

  const { data: courses = [], isLoading: isLoadingCourses, error: coursesError } = useQuery({
    queryKey: ['courses'],
    queryFn: fetchCourses,
    retry: false,
    enabled: !!studentId && !!token && role !== 'admin',
  });

  const { data: mySchedule = [], isLoading: isLoadingSchedule } = useQuery({
    queryKey: ['my-schedule'],
    queryFn: fetchMySchedule,
    retry: 1,
    enabled: !!studentId && !!token && role !== 'admin',
  });

  const registerMutation = useMutation({
    mutationFn: registerCourse,
    onSuccess: (data) => {
      toast.success(data.message || 'Đăng ký thành công.');
      queryClient.invalidateQueries({ queryKey: ['courses'] });
      queryClient.invalidateQueries({ queryKey: ['my-schedule'] });
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: cancelRegistration,
    onSuccess: (data) => {
      toast.success(data.message || 'Hủy đăng ký thành công.');
      queryClient.invalidateQueries({ queryKey: ['courses'] });
      queryClient.invalidateQueries({ queryKey: ['my-schedule'] });
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  if (!mounted || !studentId || !token || role === 'admin') return null;

  const myScheduleIds = new Set(mySchedule.map(c => c.id));

  const handleCheckboxChange = (course: CourseClass) => {
    const isRegistered = myScheduleIds.has(course.id);
    if (isRegistered) {
      cancelMutation.mutate(course.id);
    } else {
      registerMutation.mutate({ courseClassId: course.id });
    }
  };

  // Timetable grid rendering helper
  const renderTimetable = () => {
    const days = [2, 3, 4, 5, 6, 7, 8];
    const periods = Array.from({ length: 12 }, (_, i) => i + 1);

    return (
      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-zinc-200 text-sm min-w-[600px]">
          <thead>
            <tr>
              <th className="border border-zinc-200 bg-zinc-50 p-2 w-16">Tiết</th>
              {days.map(d => (
                <th key={d} className="border border-zinc-200 bg-zinc-50 p-2">
                  {d === 8 ? 'Chủ nhật' : `Thứ ${d}`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {periods.map(period => (
              <tr key={period}>
                <td className="border border-zinc-200 bg-zinc-50 p-2 text-center font-medium">{period}</td>
                {days.map(day => {
                  // Find course in this slot
                  const courseInSlot = mySchedule.find(c => 
                    c.schedules.some(s => s.day_of_week === day && period >= s.start_period && period <= s.end_period)
                  );

                  if (courseInSlot) {
                    const schedule = courseInSlot.schedules.find(s => s.day_of_week === day && period >= s.start_period && period <= s.end_period)!;
                    
                    // If this is the starting period, render with rowSpan
                    if (period === schedule.start_period) {
                      const rowSpan = schedule.end_period - schedule.start_period + 1;
                      return (
                        <td key={`${day}-${period}`} rowSpan={rowSpan} className="border border-zinc-200 bg-blue-50 p-2 align-middle">
                          <div className="text-xs text-blue-700 font-semibold text-center flex flex-col items-center justify-center space-y-1">
                            <span className="font-bold">{courseInSlot.course_name}</span>
                            <span>{courseInSlot.class_code}</span>
                            <span className="text-blue-500">{courseInSlot.room}</span>
                          </div>
                        </td>
                      );
                    }
                    // If it's a subsequent period, skip rendering the td
                    return null;
                  }

                  // No course in this slot
                  return (
                    <td key={`${day}-${period}`} className="border border-zinc-200 p-2">
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <main className="min-h-screen bg-zinc-100 px-6 py-10">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-zinc-900">Đăng ký học phần</h1>
            <p className="mt-2 text-zinc-600">Sinh viên: <strong>{studentId}</strong></p>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/history" className="text-sm font-medium text-zinc-700 hover:text-zinc-900 transition">
              Lịch sử đăng ký
            </Link>
            <button onClick={logout} className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition">
              Đăng xuất
            </button>
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Left Column: Course List (Tick list) */}
          <div className="lg:col-span-2 space-y-6">
            {coursesError ? (
              <div className="rounded-xl bg-red-50 border border-red-200 p-8 text-center flex flex-col items-center justify-center min-h-[300px]">
                <h2 className="text-xl font-semibold text-red-700 mb-2">Chưa đến đợt đăng ký</h2>
                <p className="text-red-600">{coursesError.message}</p>
              </div>
            ) : (
              <section className="rounded-xl bg-white shadow-sm overflow-hidden border border-zinc-200">
                <div className="border-b border-zinc-200 px-6 py-4">
                  <h2 className="text-xl font-semibold text-zinc-900">Danh sách học phần (Tick list)</h2>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-zinc-50 text-zinc-600 border-b border-zinc-200">
                      <tr>
                        <th className="px-6 py-3 font-medium">Chọn</th>
                        <th className="px-6 py-3 font-medium">Mã MH</th>
                        <th className="px-6 py-3 font-medium">Mã Lớp</th>
                        <th className="px-6 py-3 font-medium text-center">TC</th>
                        <th className="px-6 py-3 font-medium">Sĩ số</th>
                        <th className="px-6 py-3 font-medium">Lịch học</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200">
                      {isLoadingCourses ? (
                        <tr>
                          <td colSpan={6} className="px-6 py-8 text-center text-zinc-500">Đang tải...</td>
                        </tr>
                      ) : courses.sort((a, b) => a.class_code.localeCompare(b.class_code)).map(course => {
                        const isRegistered = myScheduleIds.has(course.id);
                        const isFull = course.current_capacity >= course.max_capacity;
                        const isInvalid = !isRegistered && (isFull || course.is_valid === false);
                        const isProcessing = (registerMutation.isPending && registerMutation.variables?.courseClassId === course.id) || 
                                             (cancelMutation.isPending && cancelMutation.variables === course.id);
                        
                        const scheduleText = course.schedules.length > 0 
                          ? course.schedules.map(s => `T${s.day_of_week}(${s.start_period}-${s.end_period})`).join(', ')
                          : 'Chưa xếp lịch';

                        return (
                          <tr key={course.id} className={`hover:bg-zinc-50 transition ${isRegistered ? 'bg-blue-50/50 hover:bg-blue-50' : ''} ${isInvalid ? 'bg-zinc-100 opacity-50' : ''}`}>
                            <td className="px-6 py-4">
                              <input 
                                type="checkbox"
                                checked={isRegistered}
                                disabled={isProcessing || isInvalid}
                                onChange={() => handleCheckboxChange(course)}
                                className="h-5 w-5 rounded border-zinc-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50 cursor-pointer"
                              />
                            </td>
                            <td className="px-6 py-4 font-medium text-zinc-900">{course.course_code}</td>
                            <td className="px-6 py-4 text-zinc-700">{course.class_code}</td>
                            <td className="px-6 py-4 text-center">{course.credits}</td>
                            <td className="px-6 py-4 text-zinc-700">{course.current_capacity}/{course.max_capacity}</td>
                            <td className="px-6 py-4 text-zinc-700">{scheduleText}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </div>

          {/* Right Column: Preview */}
          <div className="space-y-6">
            <section className="rounded-xl bg-white shadow-sm border border-zinc-200 p-6">
              <h2 className="text-lg font-semibold text-zinc-900 mb-4">Preview TKB</h2>
              {renderTimetable()}
            </section>

            <section className="rounded-xl bg-white shadow-sm border border-zinc-200 p-6">
              <h2 className="text-lg font-semibold text-zinc-900 mb-4">Danh sách đã đăng ký</h2>
              {isLoadingSchedule ? (
                <div className="text-sm text-zinc-500">Đang tải...</div>
              ) : mySchedule.length === 0 ? (
                <div className="text-sm text-zinc-500">Chưa đăng ký môn nào.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left border-collapse border border-zinc-200">
                    <thead className="bg-zinc-50 text-zinc-600">
                      <tr>
                        <th className="border border-zinc-200 px-3 py-2">Mã MH</th>
                        <th className="border border-zinc-200 px-3 py-2">Tên môn</th>
                        <th className="border border-zinc-200 px-3 py-2">Mã Lớp</th>
                        <th className="border border-zinc-200 px-3 py-2 text-center">TC</th>
                        <th className="border border-zinc-200 px-3 py-2">Thứ</th>
                        <th className="border border-zinc-200 px-3 py-2">Ca</th>
                        <th className="border border-zinc-200 px-3 py-2">Phòng</th>
                        <th className="border border-zinc-200 px-3 py-2">Giảng viên</th>
                        <th className="border border-zinc-200 px-3 py-2">Ghi chú</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mySchedule.map(course => {
                        const daysText = course.schedules.map(s => s.day_of_week === 8 ? 'CN' : `T${s.day_of_week}`).join(', ');
                        const periodsText = course.schedules.map(s => `${s.start_period}-${s.end_period}`).join(', ');
                        return (
                          <tr key={course.id} className="hover:bg-zinc-50">
                            <td className="border border-zinc-200 px-3 py-2">{course.course_code}</td>
                            <td className="border border-zinc-200 px-3 py-2">{course.course_name}</td>
                            <td className="border border-zinc-200 px-3 py-2">{course.class_code}</td>
                            <td className="border border-zinc-200 px-3 py-2 text-center">{course.credits}</td>
                            <td className="border border-zinc-200 px-3 py-2">{daysText}</td>
                            <td className="border border-zinc-200 px-3 py-2">{periodsText}</td>
                            <td className="border border-zinc-200 px-3 py-2">{course.room}</td>
                            <td className="border border-zinc-200 px-3 py-2">{course.lecturer}</td>
                            <td className="border border-zinc-200 px-3 py-2">{course.note}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  <div className="mt-4 text-right font-medium text-zinc-900">
                    Tổng số tín chỉ: {mySchedule.reduce((sum, course) => sum + course.credits, 0)}
                  </div>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
