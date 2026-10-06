'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/useAuthStore';
import { toast } from 'sonner';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type RegistrationSession = {
  id: number;
  semester_code: string;
  start_time: string;
  end_time: string;
  allowed_cohorts: string[];
  is_cancelled: boolean;
};

const fetchSessions = async (token: string): Promise<RegistrationSession[]> => {
  const response = await fetch(`${API_URL}/api/admin/sessions`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) throw new Error('Failed to fetch sessions');
  return response.json();
};

const createSession = async (data: {
  semester_code: string;
  start_time: string;
  end_time: string;
  allowed_cohorts: string[];
  token: string;
}) => {
  const { token, ...body } = data;
  const response = await fetch(`${API_URL}/api/admin/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error('Failed to create session');
  return response.json();
};

const cancelSession = async ({ id, token }: { id: number; token: string }) => {
  const response = await fetch(`${API_URL}/api/admin/sessions/${id}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to cancel session');
  }
  return response.json();
};

const fetchCohorts = async (token: string): Promise<string[]> => {
  const response = await fetch(`${API_URL}/api/admin/cohorts`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) return ['QH-2020-I/CQ', 'QH-2021-I/CQ', 'QH-2022-I/CQ']; // fallback
  return response.json();
};

const fetchSemesters = async (token: string): Promise<string[]> => {
  const response = await fetch(`${API_URL}/api/admin/semesters`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) return ['20241', '20242']; // fallback
  return response.json();
};

export default function AdminSessionsPage() {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();

  const [semesterCode, setSemesterCode] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [selectedCohorts, setSelectedCohorts] = useState<string[]>([]);

  const [sessionToCancel, setSessionToCancel] = useState<RegistrationSession | null>(null);

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['admin-sessions'],
    queryFn: () => fetchSessions(token as string),
    enabled: !!token,
  });

  const { data: availableCohorts } = useQuery({
    queryKey: ['admin-cohorts'],
    queryFn: () => fetchCohorts(token as string),
    enabled: !!token,
  });

  const { data: availableSemesters } = useQuery({
    queryKey: ['admin-semesters'],
    queryFn: () => fetchSemesters(token as string),
    enabled: !!token,
  });

  const createMutation = useMutation({
    mutationFn: createSession,
    onSuccess: () => {
      toast.success('Tạo phiên thành công');
      setSemesterCode('');
      setStartTime('');
      setEndTime('');
      setSelectedCohorts([]);
      queryClient.invalidateQueries({ queryKey: ['admin-sessions'] });
    },
    onError: () => toast.error('Tạo phiên thất bại'),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelSession,
    onSuccess: () => {
      toast.success('Hủy phiên thành công');
      setSessionToCancel(null);
      queryClient.invalidateQueries({ queryKey: ['admin-sessions'] });
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Hủy phiên thất bại');
      setSessionToCancel(null);
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    if (!semesterCode || !startTime || !endTime || selectedCohorts.length === 0) {
      toast.error('Vui lòng điền đủ thông tin và chọn ít nhất 1 khóa');
      return;
    }
    createMutation.mutate({
      semester_code: semesterCode,
      start_time: new Date(startTime).toISOString(),
      end_time: new Date(endTime).toISOString(),
      allowed_cohorts: selectedCohorts,
      token,
    });
  };

  const confirmCancel = () => {
    if (!sessionToCancel || !token) return;
    cancelMutation.mutate({ id: sessionToCancel.id, token });
  };

  const toggleCohort = (c: string) => {
    setSelectedCohorts((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));
  };

  return (
    <div className="grid gap-6 md:grid-cols-3">
      {/* Cột 1: Form tạo */}
      <div className="md:col-span-1 space-y-6">
        <section className="rounded-xl bg-white p-6 shadow-sm border border-zinc-200">
          <h2 className="text-xl font-semibold text-zinc-900 mb-4">Tạo Phiên Đăng ký</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label
                htmlFor="semesterCode"
                className="block text-sm font-medium text-zinc-700 mb-1"
              >
                Mã học kỳ
              </label>
              <select
                id="semesterCode"
                value={semesterCode}
                onChange={(e) => setSemesterCode(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 focus:border-zinc-500 focus:outline-none"
                required
              >
                <option value="" disabled>
                  -- Chọn học kỳ --
                </option>
                {availableSemesters?.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="startTime" className="block text-sm font-medium text-zinc-700 mb-1">
                Thời gian bắt đầu
              </label>
              <input
                id="startTime"
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 focus:border-zinc-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label htmlFor="endTime" className="block text-sm font-medium text-zinc-700 mb-1">
                Thời gian kết thúc
              </label>
              <input
                id="endTime"
                type="datetime-local"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 focus:border-zinc-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label htmlFor="cohorts" className="block text-sm font-medium text-zinc-700 mb-2">
                Khóa được phép đăng ký
              </label>
              <div
                id="cohorts"
                className="space-y-2 max-h-40 overflow-y-auto border border-zinc-200 rounded-lg p-3"
              >
                {availableCohorts?.map((c) => (
                  <label key={c} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedCohorts.includes(c)}
                      onChange={() => toggleCohort(c)}
                      className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                    />
                    <span className="text-sm text-zinc-700">{c}</span>
                  </label>
                ))}
                {!availableCohorts && <p className="text-sm text-zinc-500">Đang tải...</p>}
              </div>
            </div>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="w-full rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 transition disabled:opacity-50"
            >
              {createMutation.isPending ? 'Đang tạo...' : 'Tạo phiên'}
            </button>
          </form>
        </section>
      </div>

      {/* Cột 2: Preview lịch */}
      <div className="md:col-span-2">
        <section className="rounded-xl bg-white p-6 shadow-sm border border-zinc-200">
          <h2 className="text-xl font-semibold text-zinc-900 mb-4">Lịch trình & Trạng thái</h2>

          {isLoading ? (
            <p className="text-zinc-500">Đang tải...</p>
          ) : sessions && sessions.length > 0 ? (
            <div className="space-y-4">
              {sessions.map((session) => {
                const now = new Date();
                const start = new Date(session.start_time);
                const end = new Date(session.end_time);

                let status: 'ended' | 'active' | 'upcoming' | 'cancelled';
                if (session.is_cancelled) {
                  status = 'cancelled';
                } else if (now > end) {
                  status = 'ended';
                } else if (now >= start && now <= end) {
                  status = 'active';
                } else {
                  status = 'upcoming';
                }

                const statusStyles = {
                  ended: 'bg-zinc-100 border-zinc-300',
                  active: 'bg-emerald-50 border-emerald-300 shadow-sm ring-1 ring-emerald-200',
                  upcoming: 'bg-blue-50 border-blue-300',
                  cancelled: 'bg-red-50 border-red-300 opacity-75',
                };

                const badgeStyles = {
                  ended: 'bg-zinc-200 text-zinc-700',
                  active: 'bg-emerald-500 text-white animate-pulse',
                  upcoming: 'bg-blue-500 text-white',
                  cancelled: 'bg-red-500 text-white',
                };

                const badgeText = {
                  ended: 'Đã kết thúc',
                  active: 'Đang hoạt động',
                  upcoming: 'Sắp tới',
                  cancelled: 'Đã hủy',
                };

                return (
                  <div
                    key={session.id}
                    className={`relative rounded-xl border p-4 ${statusStyles[status]} transition-all`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-3 mb-2">
                          <span
                            className={`px-2 py-1 rounded text-xs font-semibold ${badgeStyles[status]}`}
                          >
                            {badgeText[status]}
                          </span>
                          <span className="text-sm font-medium text-zinc-800">
                            ID: {session.id}
                          </span>
                        </div>
                        <p className="text-sm text-zinc-700">
                          <strong>Bắt đầu:</strong> {start.toLocaleString('vi-VN')}
                        </p>
                        <p className="text-sm text-zinc-700">
                          <strong>Kết thúc:</strong> {end.toLocaleString('vi-VN')}
                        </p>
                        <p className="text-sm text-zinc-700 mt-1">
                          <strong>Học kỳ:</strong> {session.semester_code}
                        </p>
                        <p className="text-sm text-zinc-700 mt-1">
                          <strong>Khóa:</strong> {session.allowed_cohorts.join(', ')}
                        </p>
                      </div>

                      {status === 'upcoming' && (
                        <button
                          onClick={() => setSessionToCancel(session)}
                          className="flex h-8 w-8 items-center justify-center rounded-full bg-white border border-red-200 text-red-500 hover:bg-red-50 hover:text-red-600 transition"
                          title="Hủy phiên"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-zinc-500 text-center py-8">Chưa có phiên đăng ký nào.</p>
          )}
        </section>
      </div>

      {/* Modal Hủy */}
      {sessionToCancel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-zinc-900 mb-2">Xác nhận Hủy Phiên</h3>
            <p className="text-zinc-600 mb-6">
              Bạn có chắc chắn muốn hủy phiên đăng ký bắt đầu từ{' '}
              <strong>{new Date(sessionToCancel.start_time).toLocaleString('vi-VN')}</strong> không?
              Hành động này không thể hoàn tác.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setSessionToCancel(null)}
                className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition"
              >
                Đóng
              </button>
              <button
                onClick={confirmCancel}
                disabled={cancelMutation.isPending}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition disabled:opacity-50"
              >
                {cancelMutation.isPending ? 'Đang xử lý...' : 'Xác nhận hủy'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
