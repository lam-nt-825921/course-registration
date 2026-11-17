import json
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.registration import ClassSchedule
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_keys import (
    ACTIVE_SESSION_CONFIG_KEY,
    CATALOG_READY_KEY,
    catalog_class_key,
    slot_counter_key,
    student_state_key,
)
from src.infrastructure.cache.warmup_service import CacheWarmupService
from src.infrastructure.database.models import Student as StudentModel
from src.infrastructure.repositories.sql_course_repository import SQLStudentRepository


class CatalogReadAdapter:
    @staticmethod
    async def get_or_load_student_state(student_id: UUID, db: AsyncSession) -> dict:
        redis = get_redis()
        key = student_state_key(str(student_id))
        cached = await redis.get(key)
        if cached is not None:
            return json.loads(cached)

        student = await SQLStudentRepository(db).get_by_id(student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")

        # The repository's domain Student does not expose major_id.
        result = await db.execute(
            select(StudentModel.major_id).where(StudentModel.user_id == student_id)
        )
        major_id = result.scalar_one_or_none()
        enrolled_classes = []
        for enrollment in student.enrollments:
            if enrollment.status != "enrolled":
                continue
            course_class = enrollment.course_class
            course = course_class.course
            enrolled_classes.append(
                {
                    "class_id": str(course_class.id),
                    "course_id": course.id,
                    "credits": course.credits,
                    "course_type": course.course_type,
                    "schedules": [
                        {
                            "day_of_week": schedule.day_of_week,
                            "start_period": schedule.start_period,
                            "end_period": schedule.end_period,
                        }
                        for schedule in course_class.schedules
                    ],
                }
            )

        state = {
            "cohort": student.cohort,
            "major_id": major_id,
            "passed_course_ids": sorted(
                {t.course_id for t in student.transcripts if t.status == "passed"}
            ),
            "taken_course_ids": sorted({t.course_id for t in student.transcripts}),
            "enrolled_classes": enrolled_classes,
        }
        await redis.setex(key, 1800, json.dumps(state, ensure_ascii=False))
        return state

    @staticmethod
    async def check_session_on_ram(student_cohort: str, db: AsyncSession) -> bool:
        redis = get_redis()
        cached = await redis.get(ACTIVE_SESSION_CONFIG_KEY)
        if cached is None:
            await CacheWarmupService.warmup_catalog_and_session(db)
            cached = await redis.get(ACTIVE_SESSION_CONFIG_KEY)

        sessions = json.loads(cached) if cached is not None else []
        now = datetime.now()
        for session in sessions:
            if (
                session["is_cancelled"] is False
                and datetime.fromisoformat(session["start_time"]) <= now
                <= datetime.fromisoformat(session["end_time"])
                and student_cohort in session["allowed_cohorts"]
            ):
                return True
        raise HTTPException(status_code=403, detail="Ngoài thời gian đăng ký của bạn")

    @staticmethod
    async def _load_classes_from_ram(class_ids: list[str]) -> list[dict]:
        if not class_ids:
            return []
        # Read catalog data and live counters together in one Redis command.
        keys = [catalog_class_key(class_id) for class_id in class_ids]
        keys.extend(slot_counter_key(class_id) for class_id in class_ids)
        values = await get_redis().mget(keys)
        count = len(class_ids)
        classes = []
        for catalog, counter in zip(values[:count], values[count:]):
            # Do not infer available seats from an incomplete cache record.
            if catalog is None or counter is None:
                continue
            course_class = json.loads(catalog)
            course_class["current_capacity"] = int(counter)
            classes.append(course_class)
        return classes

    @staticmethod
    async def query_courses_from_ram(
        student_id: UUID,
        keyword: str | None,
        can_register: bool | None,
        day_of_week: int | None,
        course_type: str | None,
        page: int,
        size: int,
        db: AsyncSession,
    ) -> dict:
        if page < 1 or size < 1:
            raise HTTPException(status_code=422, detail="page và size phải lớn hơn 0")

        redis = get_redis()
        if await redis.get(CATALOG_READY_KEY) is None:
            await CacheWarmupService.warmup_catalog_and_session(db)

        state = await CatalogReadAdapter.get_or_load_student_state(student_id, db)
        await CatalogReadAdapter.check_session_on_ram(state["cohort"], db)

        major_id = state["major_id"]
        index_keys = [
            f"index:major:{major_id}" if major_id is not None else "index:all_classes"
        ]
        if day_of_week is not None:
            index_keys.append(f"index:day:{day_of_week}")
        if course_type:
            course_type = getattr(course_type, "value", course_type)
            index_keys.append(f"index:type:{course_type}")
        class_ids = list(await redis.sinter(index_keys))
        classes = await CatalogReadAdapter._load_classes_from_ram(class_ids)

        if keyword:
            keyword = keyword.lower()
            classes = [
                course_class for course_class in classes
                if any(
                    keyword in course_class[field].lower()
                    for field in ("class_code", "course_code", "course_name")
                )
            ]
        if can_register:
            classes = [
                course_class for course_class in classes
                if course_class["current_capacity"] < course_class["max_capacity"]
            ]
        classes.sort(key=lambda course_class: course_class["class_code"])
        total = len(classes)
        offset = (page - 1) * size
        items = classes[offset:offset + size]

        enrolled_classes = state["enrolled_classes"]
        enrolled_ids = {course_class["class_id"] for course_class in enrolled_classes}
        passed_ids = set(state["passed_course_ids"])
        taken_ids = set(state["taken_course_ids"])
        # Match Student.get_total_registered_credits() and CourseService:
        # exclude enrolled PE credits, then add the candidate's credits.
        registered_credits = sum(
            course_class["credits"] for course_class in enrolled_classes
            if course_class["course_type"] != "physical_education"
        )
        physical_education_count = sum(
            course_class["course_type"] == "physical_education"
            for course_class in enrolled_classes
        )
        registered_schedules = [
            ClassSchedule(**schedule)
            for course_class in enrolled_classes
            for schedule in course_class["schedules"]
        ]
        for course_class in items:
            course_class["note"] = (
                "Học lại" if course_class["course_id"] in taken_ids else "Học lần đầu"
            )
            course_class["is_valid"] = course_class["id"] in enrolled_ids or (
                course_class["current_capacity"] < course_class["max_capacity"]
                and registered_credits + course_class["credits"] <= 25
                and passed_ids.issuperset(course_class["prereq_ids"])
                and (
                    course_class["course_type"] != "physical_education"
                    or physical_education_count < 1
                )
                and not any(
                    registered.conflicts_with(ClassSchedule(**schedule))
                    for schedule in course_class["schedules"]
                    for registered in registered_schedules
                )
            )

        pages = (total + size - 1) // size
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "next": page + 1 if page < pages else None,
            "prev": page - 1 if page > 1 else None,
        }

    @staticmethod
    async def get_my_schedule_from_ram(student_id: UUID, db: AsyncSession) -> list[dict]:
        state = await CatalogReadAdapter.get_or_load_student_state(student_id, db)
        class_ids = [course_class["class_id"] for course_class in state["enrolled_classes"]]
        if not class_ids:
            return []
        classes = await CatalogReadAdapter._load_classes_from_ram(class_ids)
        taken_ids = set(state["taken_course_ids"])
        for course_class in classes:
            course_class["note"] = (
                "Học lại" if course_class["course_id"] in taken_ids else "Học lần đầu"
            )
        return classes
