"""
Shared Redis Key Schema Contract for Phase 2 High-Concurrency Optimization.
Dùng thống nhất cho cả 3 thành viên (Luồng Ghi, Luồng Đọc/Warm-up và Gatekeeper/Session/Audit).
"""

# 1. Cờ trạng thái & Khóa tái tạo RAM (Người 1 & Người 2)
CATALOG_READY_KEY = "catalog:ready"
REBUILD_LOCK_KEY = "lock:rebuild_ram"
ACTIVE_SESSION_CONFIG_KEY = "session:active_config"

# 2. Khóa Phiên đăng nhập & Gatekeeper (Người 3)
SESSION_LIMIT_TOGGLE_KEY = "config:session_limit_enabled"
ONLINE_STUDENTS_ZSET = "session:online_students"
AUDIT_QUEUE_KEY = "audit:queue"

# 3. Khóa Tập chỉ mục Tìm kiếm trên RAM (Người 2)
INDEX_ALL_CLASSES_KEY = "index:all_classes"


def catalog_class_key(class_id: str) -> str:
    """JSON thông tin tĩnh của 1 lớp học phần (Catalog_View)."""
    return f"catalog:class:{class_id}"


def slot_counter_key(class_id: str) -> str:
    """Integer sĩ số hiện tại (current_capacity) của lớp học phần (Slot_Counter)."""
    return f"slot:counter:{class_id}"


def student_state_key(student_id: str) -> str:
    """JSON trạng thái học tập & đăng ký của sinh viên đang online (TTL = 1800s)."""
    return f"student:state:{student_id}"


def student_lock_key(student_id: str) -> str:
    """Mutex Lock theo từng sinh viên chống bấm nhiều tab cùng lúc (TTL = 5s)."""
    return f"lock:student:{student_id}"


def session_lease_key(student_id: str) -> str:
    """JSON hợp đồng phiên 30 phút học + 20 phút chờ của sinh viên."""
    return f"session:lease:{student_id}"


def index_day_key(day_of_week: int) -> str:
    """Redis Set chứa danh sách class_id có lịch học vào thứ day_of_week (2..8)."""
    return f"index:day:{day_of_week}"


def index_type_key(course_type: str) -> str:
    """Redis Set chứa danh sách class_id theo loại học phần."""
    return f"index:type:{course_type}"


def index_major_key(major_id: int) -> str:
    """Redis Set chứa danh sách class_id thuộc ngành học."""
    return f"index:major:{major_id}"
