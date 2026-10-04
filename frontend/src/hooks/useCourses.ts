import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface CourseClass {
  id: string;
  class_code: string;
  course_id: number;
  credits: number;
  day_of_week: number;
  start_period: number;
  end_period: number;
  curent_capacity: number;
}

export interface CourseFilterParams {
  search?: string;
  dayOfWeek?: number;
  start_period?: string;
}

export function useCourses(filters: CourseFilterParams) {
  return useQuery({
    queryKey: ['courses', filters],
    queryFn: async () => {
      // [CẦN SỬA LOGIC DỰ ÁN]: Thay đổi Endpoint lấy danh sách lớp học phần
      const response = await api.get<CourseClass[]>('/courses', {
        params: filters,
      });
      return response.data;
    },
  });
}
