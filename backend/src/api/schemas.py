from pydantic import BaseModel, UUID4, Field
from typing import List, Optional
from datetime import datetime

class ClassScheduleSchema(BaseModel):
    day_of_week: int = Field(..., description="Thứ trong tuần (2-8)")
    start_period: int = Field(..., description="Tiết bắt đầu (1-12)")
    end_period: int = Field(..., description="Tiết kết thúc (1-12)")

    class Config:
        from_attributes = True

class CourseClassResponse(BaseModel):
    id: UUID4
    class_code: str
    course_code: str = Field(..., description="Mã môn học")
    credits: int
    course_type: str
    max_capacity: int
    current_capacity: int
    schedules: List[ClassScheduleSchema]

    class Config:
        from_attributes = True

class EnrollmentHistoryResponse(BaseModel):
    semester_code: str
    course_classes: List[CourseClassResponse]

    class Config:
        from_attributes = True

class RegisterCourseRequest(BaseModel):
    student_id: UUID4 = Field(..., description="Mã sinh viên đăng ký")
    course_class_id: UUID4 = Field(..., description="Mã lớp học phần (UUID)")

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
