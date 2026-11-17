import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_keys import (
    ACTIVE_SESSION_CONFIG_KEY,
    CATALOG_READY_KEY,
    catalog_class_key,
    slot_counter_key,
)
from src.infrastructure.database.models import (
    Course,
    CourseClass,
    Major,
    MajorCourse,
    RegistrationSession,
)


class CacheWarmupService:
    @staticmethod
    async def warmup_catalog_and_session(
        db: AsyncSession, force_reset_slots: bool = False
    ) -> None:
        stmt = select(CourseClass).options(
            selectinload(CourseClass.course).selectinload(Course.prerequisites),
            selectinload(CourseClass.schedules),
        )
        result = await db.execute(stmt)
        classes = result.scalars().unique().all()

        result = await db.execute(select(MajorCourse))
        course_to_majors = {}
        for mapping in result.scalars().all():
            course_to_majors.setdefault(mapping.course_id, []).append(mapping.major_id)

        result = await db.execute(select(Major.id))
        all_major_ids = result.scalars().all()

        now = datetime.now()
        stmt = (
            select(RegistrationSession)
            .where(
                RegistrationSession.is_cancelled.is_(False),
                RegistrationSession.end_time >= now,
            )
            .order_by(RegistrationSession.start_time.asc())
        )
        result = await db.execute(stmt)
        sessions_payload = [
            {
                "id": session.id,
                "allowed_cohorts": session.allowed_cohorts,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat(),
                "is_cancelled": session.is_cancelled,
            }
            for session in result.scalars().all()
        ]

        redis = get_redis()
        async with redis.pipeline() as pipe:
            old_index_keys = await redis.keys("index:*")
            if old_index_keys:
                pipe.delete(*old_index_keys)

            for course_class in classes:
                class_id = str(course_class.id)
                course = course_class.course
                course_type = getattr(course.course_type, "value", course.course_type)
                schedules = [
                    {
                        "day_of_week": schedule.day_of_week,
                        "start_period": schedule.start_period,
                        "end_period": schedule.end_period,
                    }
                    for schedule in course_class.schedules
                ]
                class_data = {
                    "id": class_id,
                    "class_code": course_class.class_code,
                    "course_id": course.id,
                    "course_code": course.course_code,
                    "course_name": course.name,
                    "credits": course.credits,
                    "course_type": course_type,
                    "room": course_class.room or "",
                    "lecturer": course_class.lecturer or "",
                    "max_capacity": course_class.max_capacity,
                    "prereq_ids": [prereq.prereq_id for prereq in course.prerequisites],
                    "schedules": schedules,
                }
                pipe.set(catalog_class_key(class_id), json.dumps(class_data))
                if force_reset_slots:
                    pipe.set(slot_counter_key(class_id), course_class.current_capacity)
                else:
                    pipe.setnx(slot_counter_key(class_id), course_class.current_capacity)

                pipe.sadd("index:all_classes", class_id)
                pipe.sadd(f"index:type:{course_type}", class_id)
                for schedule in schedules:
                    pipe.sadd(f"index:day:{schedule['day_of_week']}", class_id)

                target_majors = course_to_majors.get(course.id, all_major_ids)
                for major_id in target_majors:
                    pipe.sadd(f"index:major:{major_id}", class_id)

            pipe.set(ACTIVE_SESSION_CONFIG_KEY, json.dumps(sessions_payload))
            pipe.set(CATALOG_READY_KEY, "1")
            await pipe.execute()
