"""Init 10 tables

Revision ID: 001
Revises: 
Create Date: 2026-09-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create ENUMs
    role_enum = postgresql.ENUM('student', 'admin', name='roleenum')
    role_enum.create(op.get_bind())
    
    course_type_enum = postgresql.ENUM('normal', 'physical_education', name='coursetypeenum')
    course_type_enum.create(op.get_bind())
    
    enrollment_status_enum = postgresql.ENUM('enrolled', 'cancelled', name='enrollmentstatusenum')
    enrollment_status_enum.create(op.get_bind())
    
    transcript_status_enum = postgresql.ENUM('passed', 'failed', name='transcriptstatusenum')
    transcript_status_enum.create(op.get_bind())

    # Create tables
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', role_enum, nullable=False),
    )
    
    op.create_table(
        'students',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('student_code', sa.String(), nullable=False, unique=True),
        sa.Column('cohort', sa.String(), nullable=False),
    )

    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('course_code', sa.String(), nullable=False, unique=True),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('course_type', course_type_enum, nullable=False),
    )

    op.create_table(
        'course_prerequisites',
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), primary_key=True),
        sa.Column('prereq_id', sa.Integer(), sa.ForeignKey('courses.id'), primary_key=True),
    )

    op.create_table(
        'semesters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), default=False),
    )

    op.create_table(
        'registration_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('semester_id', sa.Integer(), sa.ForeignKey('semesters.id')),
        sa.Column('allowed_cohorts', postgresql.JSONB(), nullable=False),
        sa.Column('start_time', sa.DateTime()),
    )

    op.create_table(
        'course_classes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('class_code', sa.String(), nullable=False, unique=True),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id')),
        sa.Column('semester_id', sa.Integer(), sa.ForeignKey('semesters.id')),
        sa.Column('max_capacity', sa.Integer(), nullable=False),
        sa.Column('current_capacity', sa.Integer(), default=0),
    )

    op.create_table(
        'class_schedules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('course_class_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('course_classes.id')),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_period', sa.Integer(), nullable=False),
        sa.Column('end_period', sa.Integer(), nullable=False),
    )

    op.create_table(
        'enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.user_id')),
        sa.Column('course_class_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('course_classes.id')),
        sa.Column('status', enrollment_status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'academic_transcripts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.user_id')),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id')),
        sa.Column('status', transcript_status_enum, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('academic_transcripts')
    op.drop_table('enrollments')
    op.drop_table('class_schedules')
    op.drop_table('course_classes')
    op.drop_table('registration_sessions')
    op.drop_table('semesters')
    op.drop_table('course_prerequisites')
    op.drop_table('courses')
    op.drop_table('students')
    op.drop_table('users')
    
    # Drop ENUMs
    postgresql.ENUM(name='transcriptstatusenum').drop(op.get_bind())
    postgresql.ENUM(name='enrollmentstatusenum').drop(op.get_bind())
    postgresql.ENUM(name='coursetypeenum').drop(op.get_bind())
    postgresql.ENUM(name='roleenum').drop(op.get_bind())
