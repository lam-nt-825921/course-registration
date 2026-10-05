from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models import RegistrationSession, AuditLog, Semester

class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_sessions(self):
        stmt = select(RegistrationSession).options(selectinload(RegistrationSession.semester)).order_by(desc(RegistrationSession.start_time))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_session(self, semester_code: str, start_time: datetime, end_time: datetime, allowed_cohorts: list[str]):
        # Get or create semester
        stmt = select(Semester).where(Semester.code == semester_code)
        result = await self.session.execute(stmt)
        semester = result.scalars().first()
        if not semester:
            semester = Semester(code=semester_code, is_active=True)
            self.session.add(semester)
            await self.session.flush()

        if start_time.tzinfo:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo:
            end_time = end_time.replace(tzinfo=None)

        new_session = RegistrationSession(
            semester_id=semester.id,
            start_time=start_time,
            end_time=end_time,
            allowed_cohorts=allowed_cohorts,
            is_cancelled=False
        )
        self.session.add(new_session)
        await self.session.commit()
        return new_session

    async def cancel_session(self, session_id: int):
        stmt = select(RegistrationSession).where(RegistrationSession.id == session_id)
        result = await self.session.execute(stmt)
        session = result.scalars().first()
        if not session:
            raise ValueError("Phiên không tồn tại")
        
        now = datetime.now()
        if session.start_time <= now <= session.end_time and not session.is_cancelled:
            raise ValueError("Không thể hủy phiên đang hoạt động")
        if session.end_time < now and not session.is_cancelled:
            raise ValueError("Không thể hủy phiên đã kết thúc")

        session.is_cancelled = True
        await self.session.commit()
        return session

    async def get_logs(self):
        stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(100)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def log_action(self, student_id: UUID, course_class_id: UUID, action: str, ip_address: str = None):
        log = AuditLog(
            student_id=student_id,
            course_class_id=course_class_id,
            action=action,
            ip_address=ip_address
        )
        self.session.add(log)
        await self.session.commit()
