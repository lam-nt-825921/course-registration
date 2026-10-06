'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/store/useAuthStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type AuditLog = {
  id: number;
  student_id: string;
  course_class_id: string;
  action: string;
  timestamp: string;
  ip_address: string;
};

const fetchLogs = async (token: string): Promise<AuditLog[]> => {
  const response = await fetch(`${API_URL}/api/admin/logs`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) throw new Error('Failed to fetch logs');
  return response.json();
};

export default function AdminLogsPage() {
  const { token } = useAuthStore();
  const {
    data: logs,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['admin-logs'],
    queryFn: () => fetchLogs(token as string),
    enabled: !!token,
    refetchInterval: 10000,
  });

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm border border-zinc-200">
      <h2 className="text-xl font-semibold text-zinc-900 mb-6">Audit Logs</h2>

      {isLoading ? (
        <p className="text-zinc-500">Đang tải dữ liệu...</p>
      ) : error ? (
        <p className="text-red-500">Lỗi khi tải dữ liệu logs</p>
      ) : logs && logs.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-600">
            <thead className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-700">
              <tr>
                <th className="px-4 py-3">Thời gian</th>
                <th className="px-4 py-3">Sinh viên</th>
                <th className="px-4 py-3">Hành động</th>
                <th className="px-4 py-3">Mã lớp học phần</th>
                <th className="px-4 py-3">IP Address</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-zinc-900">
                    {new Date(log.timestamp).toLocaleString('vi-VN')}
                  </td>
                  <td className="px-4 py-3">{log.student_id}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        log.action === 'ENROLLED'
                          ? 'bg-blue-100 text-blue-700'
                          : log.action === 'CANCELLED'
                            ? 'bg-orange-100 text-orange-700'
                            : 'bg-zinc-100 text-zinc-700'
                      }`}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500 font-mono text-xs">
                    {log.course_class_id}
                  </td>
                  <td className="px-4 py-3 text-zinc-500">{log.ip_address || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-zinc-500 text-center py-8">Chưa có bản ghi log nào.</p>
      )}
    </div>
  );
}
