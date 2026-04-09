from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

class Professor(Base):
    __tablename__ = "professors"
    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(120), nullable=False)
    email      = Column(String(120), unique=True, index=True, nullable=False)
    password   = Column(String(255), nullable=False)
    department = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sections   = relationship("Section", back_populates="professor", cascade="all, delete-orphan")

class Section(Base):
    __tablename__ = "sections"
    id           = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("professors.id", ondelete="CASCADE"), nullable=False)
    name         = Column(String(80), nullable=False)
    course       = Column(String(120), nullable=False)
    year_sem     = Column(String(80), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    professor    = relationship("Professor", back_populates="sections")
    students     = relationship("Student",   back_populates="section",  cascade="all, delete-orphan")
    sessions     = relationship("QRSession", back_populates="section",  cascade="all, delete-orphan")

class Student(Base):
    __tablename__ = "students"
    id         = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    name       = Column(String(120), nullable=False)
    reg_number = Column(String(40),  unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    section    = relationship("Section",    back_populates="students")
    attendance = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")

class SessionStatus(str, enum.Enum):
    active  = "active"
    expired = "expired"

class QRSession(Base):
    __tablename__ = "qr_sessions"
    id         = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    name       = Column(String(120), nullable=False)
    token      = Column(String(64), unique=True, index=True, nullable=False)
    ttl        = Column(Integer, nullable=False, default=10)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status     = Column(Enum(SessionStatus), default=SessionStatus.active, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    prof_lat   = Column(String(30), nullable=True)
    prof_lng   = Column(String(30), nullable=True)
    geo_radius = Column(Integer, nullable=True, default=100)
    section    = relationship("Section",    back_populates="sessions")
    attendance = relationship("Attendance", back_populates="session", cascade="all, delete-orphan")

class Attendance(Base):
    __tablename__ = "attendance"
    id            = Column(Integer, primary_key=True, index=True)
    student_id    = Column(Integer, ForeignKey("students.id",    ondelete="CASCADE"), nullable=False)
    session_id    = Column(Integer, ForeignKey("qr_sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp     = Column(DateTime(timezone=True), server_default=func.now())
    layers_passed = Column(String(200), nullable=True)
    latitude      = Column(String(30), nullable=True)
    longitude     = Column(String(30), nullable=True)
    student       = relationship("Student",   back_populates="attendance")
    session       = relationship("QRSession", back_populates="attendance")
    __table_args__ = (UniqueConstraint("student_id", "session_id", name="uq_student_session"),)
