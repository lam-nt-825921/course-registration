import { toast } from 'sonner';
import { useAuthStore } from '@/store/useAuthStore';

/**
 * Gọi ngay sau fetch(). Nếu backend trả 401 (hết 30 phút phiên, hoặc đã đăng xuất ở tab khác)
 * thì xóa phiên local (các trang sẽ tự chuyển về /login) và ném lỗi.
 */
export async function throwIfUnauthorized(response: Response): Promise<void> {
  if (response.status !== 401) return;
  const data = await response.json().catch(() => ({}));
  const message = data.detail || 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.';
  useAuthStore.getState().clearAuth();
  toast.error(message);
  throw new Error(message);
}
