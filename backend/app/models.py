from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    card_uid = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    identifier = Column(String(64), nullable=True)  # Student ID / Employee Code
    department = Column(String(128), default="General")
    role = Column(String(64), default="Member")      # Student, Staff, Admin, Visitor
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("AttendanceLog", back_populates="user", cascade="all, delete-orphan")


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    card_uid = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    log_type = Column(String(32), default="CHECK_IN")  # CHECK_IN, CHECK_OUT, UNKNOWN
    device_id = Column(String(64), default="ESP32-READER-01")
    note = Column(Text, nullable=True)

    user = relationship("User", back_populates="logs")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String(256), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
