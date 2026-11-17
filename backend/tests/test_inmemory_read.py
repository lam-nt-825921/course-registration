"""Run from backend: python -m unittest discover -s tests -p test_inmemory_read.py -v."""

import json
import unittest
from datetime import datetime, timedelta
from fnmatch import fnmatch
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_student
from src.api.endpoints.courses import router
from src.api.endpoints.courses import invalidate_registration_cache
from fastapi import HTTPException
from src.api.schemas import CourseClassResponse, PaginatedCourseClassResponse
from src.infrastructure.cache.redis_keys import catalog_class_key, slot_counter_key, student_state_key
from src.infrastructure.cache.warmup_service import CacheWarmupService
from src.infrastructure.database.models import (
    ClassSchedule, Course, CourseClass, CoursePrerequisite, CourseTypeEnum,
    MajorCourse, RegistrationSession,
)
from src.infrastructure.database.session import get_db


class MemoryRedis:
    """Minimal Redis double; pipeline writes are applied only by execute()."""

    def __init__(self):
        self.data = {"index:obsolete": {"old-class"}}
        self.commands = []

    def pipeline(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.commands.clear()

    def set(self, *args):
        self.commands.append(("set", args))

    def setnx(self, *args):
        self.commands.append(("setnx", args))

    def sadd(self, *args):
        self.commands.append(("sadd", args))

    def delete(self, *args):
        self.commands.append(("delete", args))

    async def execute(self):
        for command, args in self.commands:
            key = args[0]
            if command == "set":
                self.data[key] = str(args[1])
            elif command == "setnx":
                self.data.setdefault(key, str(args[1]))
            elif command == "sadd":
                self.data.setdefault(key, set()).update(args[1:])
            elif command == "delete":
                for key in args:
                    self.data.pop(key, None)
        self.commands.clear()

    async def get(self, key):
        return self.data.get(key)

    async def keys(self, pattern):
        return [key for key in self.data if fnmatch(key, pattern)]

    async def sinter(self, keys):
        return set.intersection(*(self.data.get(key, set()) for key in keys))

    async def mget(self, keys):
        return [self.data.get(key) for key in keys]


class InMemoryReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_write_cache_is_invalidated_only_after_commit(self):
        service = MagicMock()
        service.course_class_repo.session.commit = AsyncMock()
        redis = MagicMock()
        events = []

        async def commit():
            events.append("commit")

        async def delete(*keys):
            events.append("invalidate")
            self.assertEqual(keys, (student_state_key("student"), slot_counter_key("class"), "catalog:ready"))

        service.course_class_repo.session.commit.side_effect = commit
        redis.delete = AsyncMock(side_effect=delete)
        with patch("src.api.endpoints.courses.get_redis", return_value=redis):
            await invalidate_registration_cache(service, "student", "class")
            self.assertEqual(events, ["commit", "invalidate"])
            service.course_class_repo.session.commit.side_effect = RuntimeError("commit failed")
            redis.delete.reset_mock()
            with self.assertRaises(RuntimeError):
                await invalidate_registration_cache(service, "student", "class")
            redis.delete.assert_not_awaited()

    async def test_bad_counter_returns_503_instead_of_inventing_seats(self):
        from src.infrastructure.cache.catalog_read_adapter import CatalogReadAdapter

        self.redis.data[slot_counter_key(str(self.classes[0].id))] = "broken"
        with self.assertRaises(HTTPException) as error:
            await CatalogReadAdapter._load_classes_from_ram([str(self.classes[0].id)])
        self.assertEqual(error.exception.status_code, 503)

    async def asyncSetUp(self):
        self.redis = MemoryRedis()
        for module in ("warmup_service", "catalog_read_adapter"):
            patcher = patch(f"src.infrastructure.cache.{module}.get_redis", return_value=self.redis)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.classes = []
        for number, (day, kind, prereq) in enumerate([
            (2, CourseTypeEnum.normal, 1),
            (2, CourseTypeEnum.normal, 99),
            (3, CourseTypeEnum.normal, 1),
            (2, CourseTypeEnum.physical_education, 1),
            (2, CourseTypeEnum.normal, 1),
        ], start=10):
            self.classes.append(CourseClass(
                id=uuid4(), class_code=f"INT{number} 1", max_capacity=40, current_capacity=10,
                course=Course(
                    id=number, course_code=f"INT{number}", name=f"Course {number}",
                    credits=3, course_type=kind,
                    prerequisites=[CoursePrerequisite(prereq_id=prereq)],
                ),
                schedules=[ClassSchedule(day_of_week=day, start_period=1, end_period=3)],
            ))
        now = datetime.now()
        session = RegistrationSession(
            id=1, allowed_cohorts=["K68"], is_cancelled=False,
            start_time=now - timedelta(days=1), end_time=now + timedelta(days=1),
        )
        self.db = AsyncMock(spec=AsyncSession)
        results = []
        mappings = [MajorCourse(course_id=i, major_id=2 if i == 14 else 1) for i in (10, 11, 12, 14)]
        for values in (self.classes, mappings, [1, 2], [session]):
            result = MagicMock()
            result.scalars.return_value.all.return_value = values
            result.scalars.return_value.unique.return_value.all.return_value = values
            results.append(result)
        self.db.execute.side_effect = results
        await CacheWarmupService.warmup_catalog_and_session(self.db)
        self.db.execute.reset_mock()
        self.db.execute.side_effect = AssertionError("Read path queried the database after warm-up")

        self.student_id = uuid4()
        self.state = dict(cohort="K68", major_id=1, passed_course_ids=[1],
                          taken_course_ids=[10], enrolled_classes=[])
        self.cache_student()
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/courses")
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[get_current_student] = lambda: {"student_id": self.student_id}

    def cache_student(self):
        self.redis.data[student_state_key(str(self.student_id))] = json.dumps(self.state)

    async def get(self, path, query=b""):
        # Exercise ASGI routing and response serialization without an HTTP client dependency.
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await self.app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "GET", "scheme": "http", "path": path, "raw_path": path.encode(),
            "query_string": query, "headers": [], "root_path": "",
            "client": ("127.0.0.1", 1234), "server": ("test", 80),
        }, receive, send)
        status = next(m["status"] for m in messages if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        self.assertEqual(status, 200, body)
        return json.loads(body)

    async def test_warmup_creates_catalog_counters_indexes_and_session(self):
        for course_class in self.classes:
            cid = str(course_class.id)
            catalog = json.loads(self.redis.data[catalog_class_key(cid)])
            self.assertEqual(catalog["course_id"], course_class.course.id)
            self.assertEqual(self.redis.data[slot_counter_key(cid)], "10")
            self.assertIn(cid, self.redis.data["index:all_classes"])
            self.assertIn(cid, self.redis.data[f"index:type:{course_class.course.course_type.value}"])
            self.assertIn(cid, self.redis.data[f"index:day:{course_class.schedules[0].day_of_week}"])
        common_id = str(self.classes[3].id)
        self.assertIn(common_id, self.redis.data["index:major:1"])
        self.assertIn(common_id, self.redis.data["index:major:2"])
        self.assertEqual(self.redis.data["index:major:2"], {common_id, str(self.classes[4].id)})
        self.assertNotIn("index:obsolete", self.redis.data)
        self.assertEqual(json.loads(self.redis.data["session:active_config"])[0]["id"], 1)
        self.assertEqual(self.redis.data["catalog:ready"], "1")

    async def test_combined_filters_validity_and_response_schema_without_sql(self):
        self.redis.data[slot_counter_key(str(self.classes[0].id))] = "39"
        payload = await self.get("/api/courses/", b"day_of_week=2&course_type=normal")
        self.assertEqual(set(payload), set(PaginatedCourseClassResponse.model_fields))
        self.assertEqual([item["id"] for item in payload["items"]], [str(c.id) for c in self.classes[:2]])
        self.assertEqual([item["is_valid"] for item in payload["items"]], [True, False])
        self.assertEqual([item["note"] for item in payload["items"]], ["Học lại", "Học lần đầu"])
        self.assertEqual(payload["items"][0]["current_capacity"], 39)
        self.assertEqual((payload["total"], payload["pages"], payload["next"], payload["prev"]), (2, 1, None, None))
        for item in payload["items"]:
            self.assertEqual(set(item), set(CourseClassResponse.model_fields))
        self.db.execute.assert_not_awaited()

    async def test_schedule_response_schema_and_empty_schedule_without_sql(self):
        course_class = self.classes[0]
        self.state["enrolled_classes"] = [{"class_id": str(course_class.id)}]
        self.cache_student()
        payload = await self.get("/api/courses/my-schedule")
        self.assertEqual(len(payload), 1)
        self.assertEqual(set(payload[0]), set(CourseClassResponse.model_fields))
        self.assertEqual(payload[0]["id"], str(course_class.id))
        self.assertEqual(payload[0]["note"], "Học lại")
        self.assertEqual(payload[0]["current_capacity"], 10)
        self.assertIs(payload[0]["is_valid"], True)
        self.state["enrolled_classes"] = []
        self.cache_student()
        self.assertEqual(await self.get("/api/courses/my-schedule"), [])
        self.db.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
