'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/useAuthStore';
import { parseJwt } from '@/lib/jwt';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const LIMIT_POLL_MS = 60_000;

function format(sec: number) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Đồng hồ đếm ngược phiên 30 phút của sinh viên (lấy từ `exp` trong JWT). */
export default function SessionTimer() {
  const token = useAuthStore((s) => s.token);
  const role = useAuthStore((s) => s.role);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [limitEnabled, setLimitEnabled] = useState(false);

  // Hỏi backend xem giới hạn phiên đang bật hay tắt (kiểm tra lại mỗi phút)
  useEffect(() => {
    if (!token || role !== 'student') return;
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/api/auth/session-limit`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res || !res.ok) return;
        const data = await res.json();
        if (!cancelled) setLimitEnabled(Boolean(data.limit_enabled));
      } catch {
        // lỗi mạng: giữ nguyên trạng thái hiện tại
      }
    };
    check();
    const id = setInterval(check, LIMIT_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [token, role]);

  useEffect(() => {
    const exp: number | undefined =
      token && role === 'student' && limitEnabled ? parseJwt(token)?.exp : undefined;
    if (!exp) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRemaining(null);
      return;
    }

    let timer: ReturnType<typeof setInterval> | undefined;
    const tick = () => {
      const left = Math.floor(exp - Date.now() / 1000);
      if (left <= 0) {
        toast.warning('Phiên đăng nhập 30 phút đã hết. Vui lòng chờ 20 phút.');
        clearAuth();
        if (timer) clearInterval(timer);
        return;
      }
      setRemaining(left);
    };
    tick();
    timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [token, role, limitEnabled, clearAuth]);

  if (remaining === null) return null;

  const warn = remaining <= 300;
  return (
    <span
      title="Thời gian phiên đăng nhập còn lại"
      className={`rounded-lg px-3 py-1 text-sm font-medium ${warn ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
        }`}
    >
      Phiên còn {format(remaining)}
    </span>
  );
}
