from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime

class ProfessorRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    department: Optional[str] = None
    @field_validator("password")
    @classmethod
    def pw_len(cls, v):
        if len(v) < 6: raise ValueError("Password must be at least 6 characters")
        return v

class ProfessorLogin(BaseModel):
    email: EmailStr
    password: str

class ProfessorOut(BaseModel):
    id: int; name: str; email: str; department: Optional[str]; created_at: datetime
    class Config: from_attributes = True

class TokenResponse(BaseModel):
    access_token: str; token_type: str = "bearer"; professor: ProfessorOut

class SectionCreate(BaseModel):
    name: str; course: str; year_sem: Optional[str] = None

class SectionOut(BaseModel):
    id: int; name: str; course: str; year_sem: Optional[str]; student_count: int = 0; created_at: datetime
    class Config: from_attributes = True

class StudentCreate(BaseModel):
    name: str; reg_number: str; section_id: int

class StudentOut(BaseModel):
    id: int; name: str; reg_number: str; section_id: int; created_at: datetime
    class Config: from_attributes = True

class StudentWithAttendance(StudentOut):
    attendance_count: int = 0; total_sessions: int = 0; attendance_pct: float = 0.0; section_name: str = ""

class SessionCreate(BaseModel):
    name: str; section_id: int; ttl: int = 10
    prof_lat: Optional[str] = None; prof_lng: Optional[str] = None; geo_radius: int = 100
    @field_validator("ttl")
    @classmethod
    def valid_ttl(cls, v):
        if v not in [5,10,15,20,30]: raise ValueError("TTL must be 5,10,15,20, or 30")
        return v

class SessionOut(BaseModel):
    id: int; name: str; section_id: int; token: str; ttl: int
    expires_at: datetime; status: str; created_at: datetime
    attend_count: int = 0; section_name: str = ""
    prof_lat: Optional[str] = None; prof_lng: Optional[str] = None; geo_radius: int = 100
    class Config: from_attributes = True

class AttendanceSubmit(BaseModel):
    token: str; reg_number: str
    latitude: Optional[str] = None; longitude: Optional[str] = None

class AttendanceOut(BaseModel):
    id: int; student_id: int; session_id: int; timestamp: datetime
    layers_passed: Optional[str]
    student_name: str = ""; reg_number: str = ""; section_name: str = ""; session_name: str = ""
    class Config: from_attributes = True
