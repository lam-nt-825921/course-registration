import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, 
    DateTime, Enum, PrimaryKeyConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class RoleEnum(str, enum.Enum):
    student = "student"
    admin = "admin"

class CourseTypeEnum(str, enum.Enum):
    normal = "normal"
    physical_education = "physical_education"

class EnrollmentStatusEnum(str, enum.Enum):
    enrolled = "enrolled"
    cancelled = "cancelled"

class TranscriptStatusEnum(str, enum.Enum):
    passed = "passed"
    failed = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)

    student_profile = relationship("Student", back_populates="user", uselist=False)


class Student(Base):
    __tablename__ = "students"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    student_code = Column(String, unique=True, nullable=False)
    cohort = Column(String, nullable=False)

    user = relationship("User", back_populates="student_profile")
    enrollments = relationship("Enrollment", back_populates="student")
    transcripts = relationship("AcademicTranscript", back_populates="student")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False, server_default="Unknown")
    credits = Column(Integer, nullable=False)
    course_type = Column(Enum(CourseTypeEnum), nullable=False)

    prerequisites = relationship("CoursePrerequisite", foreign_keys="[CoursePrerequisite.course_id]", back_populates="course")
    classes = relationship("CourseClass", back_populates="course")
    transcripts = relationship("AcademicTranscript", back_populates="course")


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    prereq_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)

    course = relationship("Course", foreign_keys=[course_id], back_populates="prerequisites")
    prereq_course = relationship("Course", foreign_keys=[prereq_id])


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=False)

    sessions = relationship("RegistrationSession", back_populates="semester")
    classes = relationship("CourseClass", back_populates="semester")


class RegistrationSession(Base):
    __tablename__ = "registration_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    allowed_cohorts = Column(JSONB, nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_cancelled = Column(Boolean, default=False)

    semester = relationship("Semester", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.user_id"), nullable=False)
    course_class_id = Column(UUID(as_uuid=True), ForeignKey("course_classes.id"), nullable=False)
    action = Column(String, nullable=False) # 'ENROLLED', 'CANCELLED'
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    student = relationship("Student")
    course_class = relationship("CourseClass")


class CourseClass(Base):
    __tablename__ = "course_classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_code = Column(String, unique=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))
    semester_id = Column(Integer, ForeignKey("semesters.id"))
    room = Column(String, nullable=True)
    lecturer = Column(String, nullable=True)
    max_capacity = Column(Integer, nullable=False)
    current_capacity = Column(Integer, default=0)

    course = relationship("Course", back_populates="classes")
    semester = relationship("Semester", back_populates="classes")
    schedules = relationship("ClassSchedule", back_populates="course_class")
    enrollments = relationship("Enrollment", back_populates="course_class")


class ClassSchedule(Base):
    __tablename__ = "class_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_class_id = Column(UUID(as_uuid=True), ForeignKey("course_classes.id"))
    day_of_week = Column(Integer, nullable=False)
    start_period = Column(Integer, nullable=False)
    end_period = Column(Integer, nullable=False)

    course_class = relationship("CourseClass", back_populates="schedules")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.user_id"))
    course_class_id = Column(UUID(as_uuid=True), ForeignKey("course_classes.id"))
    status = Column(Enum(EnrollmentStatusEnum), nullable=False)
    created_at = Column(DateTime, default=func.now())

    student = relationship("Student", back_populates="enrollments")
    course_class = relationship("CourseClass", back_populates="enrollments")


class AcademicTranscript(Base):
    __tablename__ = "academic_transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.user_id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    status = Column(Enum(TranscriptStatusEnum), nullable=False)

    student = relationship("Student", back_populates="transcripts")
    course = relationship("Course", back_populates="transcripts")
