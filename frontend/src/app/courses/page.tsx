'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { CourseClass } from '@/hooks/useCourses';

interface Course {
  id: string | number;
  course_code: string;
  course_name: string;
  day_of_week: number;
  start_period: number;
  credits?: number;
  lecturer?: string;
  room?: string;
  available_slots?: number;
  total_slots?: number;
}

export default function CoursesPage() {
  // State lưu các tham số lọc
  const [courseCode, setCourseCode] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState<number | ''>('');
  const [startPeriod, setStartPeriod] = useState<number | ''>('');

  const {
    data: courses,
    isLoading,
    isError,
  } = useQuery<Course[]>({
    queryKey: ['active-courses', courseCode, dayOfWeek, startPeriod],
    queryFn: async () => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;

      const params: Record<string, any> = {};

      if (courseCode.trim() !== '') {
        params.course_code = courseCode.trim();
      }
      if (dayOfWeek !== '') {
        params.day_of_week = Number(dayOfWeek);
      }
      if (startPeriod !== '') {
        params.start_period = Number(startPeriod);
      }

      const response = await axios.get('http://127.0.0.1:8000/api/courses', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        params,
      });

      return response.data;
    },
  });

  return (
    <div className="min-h-screen bg-gray-50 p-6 text-gray-800">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-emerald-800 mb-6">Tra cứu lớp học phần</h1>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6">
          <h2 className="text-md font-semibold text-gray-700 mb-4">🔍 Bộ lọc tìm kiếm</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="courseCode" className="block text-xs font-medium text-gray-600 mb-1">
                Mã môn học
              </label>
              <input
                id="courseCode"
                type="text"
                placeholder="Ví dụ: INT2204"
                value={courseCode}
                onChange={(e) => setCourseCode(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none text-sm text-black"
              />
            </div>

            <div>
              <label htmlFor="day" className="block text-xs font-medium text-gray-600 mb-1">
                Thứ
              </label>
              <select
                id="day"
                value={dayOfWeek}
                onChange={(e) => setDayOfWeek(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none text-sm text-black bg-white"
              >
                <option value="">Tất cả</option>
                <option value={2}>Thứ 2 </option>
                <option value={3}>Thứ 3 </option>
                <option value={4}>Thứ 4 </option>
                <option value={5}>Thứ 5 </option>
                <option value={6}>Thứ 6 </option>
                <option value={7}>Thứ 7 </option>
                <option value={8}>Chủ Nhật </option>
              </select>
            </div>

            <div>
              <label htmlFor="session" className="block text-xs font-medium text-gray-600 mb-1">
                Tiết học
              </label>
              <select
                id="session"
                value={startPeriod}
                onChange={(e) => setStartPeriod(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none text-sm text-black bg-white"
              >
                <option value="">Tất cả</option>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((period) => (
                  <option key={period} value={period}>
                    Tiết {period}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Đang tải danh sách học phần...</div>
          ) : isError ? (
            <div className="p-8 text-center text-red-500">
              Có lỗi xảy ra khi kết nối tới Server.
            </div>
          ) : courses && courses.length > 0 ? (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-emerald-50 text-emerald-900 text-xs font-bold uppercase border-b">
                  <th className="p-3">Mã HP</th>
                  <th className="p-3">Tên môn học</th>
                  <th className="p-3">Thứ</th>
                  <th className="p-3">Tiết bắt đầu</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-sm">
                {courses.map((course: Course) => (
                  <tr key={course.id} className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-emerald-800">{course.course_code}</td>
                    <td className="p-3 font-medium">{course.course_name}</td>
                    <td className="p-3">
                      {course.day_of_week === 8 ? 'Chủ Nhật' : `Thứ ${course.day_of_week}`}
                    </td>
                    <td className="p-3">Tiết {course.start_period}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-gray-500">Không có lớp phù hợp</div>
          )}
        </div>
      </div>
    </div>
  );
}
