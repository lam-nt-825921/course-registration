"""
Unit & Architecture Verification Tests for Phase 2 (Commits 1, 2, and 3):
- Commit 1: Shared Redis Connection Pool & Key Schema Contract.
- Commit 2: Clean Architecture AST Verification (NFR-03) & Domain Ports.
- Commit 3: Atomic Conditional Capacity Updates (Zero Overselling DB Guard) & Duplicate Enrollment Prevention.
"""
import ast
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.domain.entities.registration import Course, CourseClass, Enrollment
from src.infrastructure.cache.redis_client import get_redis, redis_pool
from src.infrastructure.cache.redis_keys import (
    ACTIVE_SESSION_CONFIG_KEY,
    AUDIT_QUEUE_KEY,
    CATALOG_READY_KEY,
    INDEX_ALL_CLASSES_KEY,
    ONLINE_STUDENTS_ZSET,
    REBUILD_LOCK_KEY,
    SESSION_LIMIT_TOGGLE_KEY,
    catalog_class_key,
    index_day_key,
    index_major_key,
    index_type_key,
    session_lease_key,
    slot_counter_key,
    student_lock_key,
    student_state_key,
)
from src.infrastructure.repositories.sql_course_repository import (
    SQLCourseClassRepository,
    SQLEnrollmentRepository,
)


class TestCommit1RedisContract(unittest.TestCase):
    """Kiểm thử Feature 1: Hợp đồng Khóa Redis & Connection Pool dùng chung."""

    def test_redis_key_generators_match_shared_contract(self):
        cid = "8f9d2a1b-3c4e-4f5a-8b9c-0d1e2f3a4b5c"
        sid = "d290f1ee-6c54-4b01-90e6-d701748f0851"

        self.assertEqual(CATALOG_READY_KEY, "catalog:ready")
        self.assertEqual(REBUILD_LOCK_KEY, "lock:rebuild_ram")
        self.assertEqual(ACTIVE_SESSION_CONFIG_KEY, "session:active_config")
        self.assertEqual(SESSION_LIMIT_TOGGLE_KEY, "config:session_limit_enabled")
        self.assertEqual(ONLINE_STUDENTS_ZSET, "session:online_students")
        self.assertEqual(AUDIT_QUEUE_KEY, "audit:queue")
        self.assertEqual(INDEX_ALL_CLASSES_KEY, "index:all_classes")

        self.assertEqual(catalog_class_key(cid), f"catalog:class:{cid}")
        self.assertEqual(slot_counter_key(cid), f"slot:counter:{cid}")
        self.assertEqual(student_state_key(sid), f"student:state:{sid}")
        self.assertEqual(student_lock_key(sid), f"lock:student:{sid}")
        self.assertEqual(session_lease_key(sid), f"session:lease:{sid}")
        self.assertEqual(index_day_key(2), "index:day:2")
        self.assertEqual(index_type_key("normal"), "index:type:normal")
        self.assertEqual(index_major_key(5), "index:major:5")

    def test_get_redis_uses_shared_pool(self):
        client = get_redis()
        self.assertIsNotNone(client)
        self.assertIs(client.connection_pool, redis_pool)


class TestCommit2CleanArchitecture(unittest.TestCase):
    """Kiểm thử Feature 2: Tầng Domain và CourseService tách biệt 100% khỏi SQLAlchemy (NFR-03)."""

    def _scan_forbidden_imports(self, file_path: Path) -> list[str]:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        violations = []
        forbidden_prefixes = ("sqlalchemy", "src.infrastructure.database")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden_prefixes):
                        violations.append(f"{file_path.name}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith(forbidden_prefixes):
                    violations.append(f"{file_path.name}:{node.lineno} from {mod} import ...")
        return violations

    def test_domain_layer_has_zero_orm_imports(self):
        domain_dir = BACKEND_DIR / "src" / "domain"
        for py_file in domain_dir.rglob("*.py"):
            violations = self._scan_forbidden_imports(py_file)
            self.assertEqual(
                violations,
                [],
                f"Phát hiện vi phạm Clean Architecture tại tầng Domain ({py_file}): {violations}",
            )

    def test_course_service_has_zero_orm_imports(self):
        course_service_file = BACKEND_DIR / "src" / "use_cases" / "course_service.py"
        violations = self._scan_forbidden_imports(course_service_file)
        self.assertEqual(
            violations,
            [],
            f"course_service.py vẫn còn import trực tiếp SQLAlchemy/Models: {violations}",
        )


class TestCommit3AtomicRepositoryAndGuard(unittest.IsolatedAsyncioTestCase):
    """Kiểm thử Feature 3: Cập nhật sĩ số nguyên tử & Chặn đăng ký trùng lặp ở mức Repository."""

    async def test_increment_capacity_atomic_success_when_slot_available(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        repo = SQLCourseClassRepository(mock_session)
        success = await repo.increment_capacity_atomic(uuid4())

        self.assertTrue(success)
        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once()

    async def test_increment_capacity_atomic_fails_when_class_full(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0  # current_capacity == max_capacity -> 0 rows updated
        mock_session.execute.return_value = mock_result

        repo = SQLCourseClassRepository(mock_session)
        success = await repo.increment_capacity_atomic(uuid4())

        self.assertFalse(success)

    async def test_decrement_capacity_atomic_prevents_negative_capacity(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0  # current_capacity == 0 -> 0 rows updated
        mock_session.execute.return_value = mock_result

        repo = SQLCourseClassRepository(mock_session)
        success = await repo.decrement_capacity_atomic(uuid4())

        self.assertFalse(success)

    async def test_enrollment_create_blocks_duplicate_active_enrollment(self):
        mock_session = AsyncMock()
        # Giả lập đã có bản ghi enrolled tồn tại
        existing_res = MagicMock()
        existing_res.scalars.return_value.first.return_value = uuid4()
        mock_session.execute.return_value = existing_res

        repo = SQLEnrollmentRepository(mock_session)
        course = Course(id=1, code="INT3306", name="Kiến trúc phần mềm", credits=3, course_type="normal")
        cc = CourseClass(
            id=uuid4(),
            class_code="INT3306_1",
            course=course,
            room="301-G2",
            lecturer="GV A",
            max_capacity=40,
            current_capacity=10,
        )
        enrollment = Enrollment(id=uuid4(), student_id=uuid4(), course_class=cc, status="enrolled")

        with self.assertRaises(ValueError) as ctx:
            await repo.create(enrollment)
        self.assertIn("đã đăng ký", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
