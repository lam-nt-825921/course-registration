import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.infrastructure.cache.warmup_service import CacheWarmupService
from src.infrastructure.database.models import (
    ClassSchedule,
    Course,
    CourseClass,
    CoursePrerequisite,
    CourseTypeEnum,
    MajorCourse,
    RegistrationSession,
    Semester,
)
from src.use_cases.admin_service import AdminService


def query_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    result.scalars.return_value.unique.return_value.all.return_value = values
    result.scalars.return_value.first.return_value = values[0] if values else None
    return result


class CacheWarmupTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_indexes_and_slot_reset_modes(self):
        for force_reset in (False, True):
            with self.subTest(force_reset=force_reset):
                course_class = CourseClass(
                    id=uuid4(), class_code="INT3306 1", max_capacity=40,
                    current_capacity=12, room=None, lecturer=None,
                    course=Course(
                        id=10, course_code="INT3306", name="Web", credits=3,
                        course_type=CourseTypeEnum.normal,
                        prerequisites=[CoursePrerequisite(prereq_id=1)],
                    ),
                    schedules=[ClassSchedule(day_of_week=2, start_period=1, end_period=3)],
                )
                common_class = CourseClass(
                    id=uuid4(), class_code="PE 1", max_capacity=50, current_capacity=0,
                    course=Course(
                        id=20, course_code="PE", name="PE", credits=2,
                        course_type=CourseTypeEnum.physical_education, prerequisites=[],
                    ),
                    schedules=[],
                )
                now = datetime.now()
                session = RegistrationSession(
                    id=5, allowed_cohorts=["K68"], start_time=now,
                    end_time=now + timedelta(days=1), is_cancelled=False,
                )
                db = AsyncMock()
                db.execute.side_effect = [
                    query_result([course_class, common_class]),
                    query_result([MajorCourse(course_id=10, major_id=1)]),
                    query_result([1, 2]), query_result([session]),
                ]
                redis = MagicMock()
                redis.keys = AsyncMock(return_value=["index:day:8", "index:major:99"])
                pipe = MagicMock()
                redis.pipeline.return_value.__aenter__.return_value = pipe
                pipe.execute = AsyncMock()
                with patch("src.infrastructure.cache.warmup_service.get_redis", return_value=redis):
                    await CacheWarmupService.warmup_catalog_and_session(db, force_reset)

                cid, common_id = str(course_class.id), str(common_class.id)
                values = {call.args[0]: call.args[1] for call in pipe.set.call_args_list}
                self.assertEqual(json.loads(values[f"catalog:class:{cid}"]), {
                    "id": cid, "class_code": "INT3306 1", "course_id": 10,
                    "course_code": "INT3306", "course_name": "Web", "credits": 3,
                    "course_type": "normal", "room": "", "lecturer": "",
                    "max_capacity": 40, "prereq_ids": [1],
                    "schedules": [{"day_of_week": 2, "start_period": 1, "end_period": 3}],
                })
                slot_command = pipe.set if force_reset else pipe.setnx
                slot_command.assert_any_call(f"slot:counter:{cid}", 12)
                slot_command.assert_any_call(f"slot:counter:{common_id}", 0)
                if force_reset:
                    pipe.setnx.assert_not_called()
                else:
                    self.assertNotIn(f"slot:counter:{cid}", values)
                pipe.delete.assert_called_once_with("index:day:8", "index:major:99")
                self.assertEqual(pipe.mock_calls[0][0], "delete")
                memberships = {call.args for call in pipe.sadd.call_args_list}
                self.assertEqual(memberships, {
                    ("index:all_classes", cid), ("index:type:normal", cid),
                    ("index:day:2", cid), ("index:major:1", cid),
                    ("index:all_classes", common_id),
                    ("index:type:physical_education", common_id),
                    ("index:major:1", common_id), ("index:major:2", common_id),
                })
                self.assertEqual(json.loads(values["session:active_config"]), [{
                    "id": 5, "allowed_cohorts": ["K68"],
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat(), "is_cancelled": False,
                }])
                session_query = db.execute.call_args_list[-1].args[0]
                sql = str(session_query)
                self.assertIn("registration_sessions.is_cancelled IS false", sql)
                self.assertIn("registration_sessions.end_time >=", sql)
                self.assertIn("ORDER BY registration_sessions.start_time ASC", sql)
                self.assertEqual(pipe.set.call_args_list[-1].args, ("catalog:ready", "1"))
                pipe.execute.assert_awaited_once()

    async def test_empty_catalog_clears_indexes_and_publishes_empty_sessions(self):
        db = AsyncMock()
        db.execute.side_effect = [query_result([]) for _ in range(4)]
        redis = MagicMock()
        redis.keys = AsyncMock(return_value=[])
        pipe = MagicMock()
        redis.pipeline.return_value.__aenter__.return_value = pipe
        pipe.execute = AsyncMock()
        with patch("src.infrastructure.cache.warmup_service.get_redis", return_value=redis):
            await CacheWarmupService.warmup_catalog_and_session(db)
        pipe.delete.assert_not_called()
        pipe.sadd.assert_not_called()
        pipe.set.assert_any_call("session:active_config", "[]")
        pipe.set.assert_any_call("catalog:ready", "1")
        pipe.execute.assert_awaited_once()

    async def test_admin_warmup_runs_after_commit(self):
        now = datetime.now()
        for action in ("create", "cancel"):
            with self.subTest(action=action):
                db = AsyncMock()
                db.add = MagicMock()
                events = []

                async def commit():
                    events.append("commit")

                async def warmup(session, force_reset_slots):
                    self.assertIs(session, db)
                    self.assertEqual(force_reset_slots, action == "create")
                    events.append("warmup")

                db.commit.side_effect = commit
                with patch.object(CacheWarmupService, "warmup_catalog_and_session", side_effect=warmup) as mocked:
                    service = AdminService(db)
                    if action == "create":
                        db.execute.return_value = query_result([Semester(id=1)])
                        result = await service.create_session("20261", now, now + timedelta(days=1), ["K68"])
                        self.assertEqual(result.semester_id, 1)
                    else:
                        session = RegistrationSession(
                            id=1, start_time=now + timedelta(days=1),
                            end_time=now + timedelta(days=2), is_cancelled=False,
                        )
                        db.execute.return_value = query_result([session])
                        self.assertIs(await service.cancel_session(1), session)
                        self.assertTrue(session.is_cancelled)
                    mocked.assert_awaited_once()
                self.assertEqual(events, ["commit", "warmup"])


if __name__ == "__main__":
    unittest.main()
