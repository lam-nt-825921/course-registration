"use client";

import { useEffect, useState } from "react";

type Course = {
  id: number;
  code: string;
  name: string;
  credits: number;
  max_slots: number;
  registered_slots: number;
};

const API_URL = "http://localhost:8000";

export default function Home() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [studentId, setStudentId] = useState("");
  const [loading, setLoading] = useState(true);
  const [registeringId, setRegisteringId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const fetchCourses = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`${API_URL}/api/courses/`);

      if (!response.ok) {
        throw new Error("Không thể tải danh sách học phần.");
      }

      const data = await response.json();
      setCourses(data);
    } catch {
      setError(
        "Không thể kết nối đến máy chủ. Vui lòng kiểm tra Backend đang chạy.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  const handleRegister = async (courseId: number) => {
    if (!studentId.trim()) {
      setError("Vui lòng nhập mã sinh viên trước khi đăng ký.");
      setMessage("");
      return;
    }

    try {
      setRegisteringId(courseId);
      setMessage("");
      setError("");

      const response = await fetch(
        `${API_URL}/api/courses/${courseId}/register?student_id=${encodeURIComponent(
          studentId,
        )}`,
        {
          method: "POST",
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Đăng ký học phần thất bại.");
      }

      setMessage(data.message || "Đăng ký học phần thành công.");

      // Tải lại danh sách để cập nhật số lượng đã đăng ký.
      await fetchCourses();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Đã xảy ra lỗi khi đăng ký học phần.");
      }
    } finally {
      setRegisteringId(null);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-100 px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-zinc-900">
            Đăng ký học phần
          </h1>

          <p className="mt-2 text-zinc-600">
            Hệ thống đăng ký môn học
          </p>
        </div>

        <section className="mb-6 rounded-xl bg-white p-6 shadow-sm">
          <label
            htmlFor="studentId"
            className="mb-2 block text-sm font-medium text-zinc-700"
          >
            Mã sinh viên
          </label>

          <input
            id="studentId"
            type="text"
            value={studentId}
            onChange={(event) => setStudentId(event.target.value)}
            placeholder="Nhập mã sinh viên"
            className="w-full rounded-lg border border-zinc-300 px-4 py-3 outline-none transition focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200"
          />
        </section>

        {message && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">
            {message}
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            {error}
          </div>
        )}

        <section className="rounded-xl bg-white shadow-sm">
          <div className="border-b border-zinc-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-zinc-900">
              Danh sách học phần
            </h2>
          </div>

          {loading ? (
            <div className="p-8 text-center text-zinc-500">
              Đang tải danh sách học phần...
            </div>
          ) : courses.length === 0 ? (
            <div className="p-8 text-center text-zinc-500">
              Hiện chưa có học phần nào.
            </div>
          ) : (
            <div className="divide-y divide-zinc-200">
              {courses.map((course) => {
                const isFull =
                  course.registered_slots >= course.max_slots;

                const isRegistering = registeringId === course.id;

                return (
                  <div
                    key={course.id}
                    className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-zinc-900">
                          {course.code}
                        </h3>

                        <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-600">
                          {course.credits} tín chỉ
                        </span>
                      </div>

                      <p className="mt-1 text-zinc-700">
                        {course.name}
                      </p>

                      <p className="mt-2 text-sm text-zinc-500">
                        Đã đăng ký: {course.registered_slots} /{" "}
                        {course.max_slots}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRegister(course.id)}
                      disabled={isFull || isRegistering}
                      className="rounded-lg bg-zinc-900 px-5 py-3 font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                    >
                      {isRegistering
                        ? "Đang đăng ký..."
                        : isFull
                          ? "Đã đầy"
                          : "Đăng ký"}
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