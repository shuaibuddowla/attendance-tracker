from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Scan models
class ScanRequest(BaseModel):
    card_uid: str
    device_id: Optional[str] = "ESP32-READER-01"

class ScanResponse(BaseModel):
    success: bool
    status: str       # CHECK_IN, CHECK_OUT, COOLDOWN, UNREGISTERED, REGISTRATION_PENDING
    card_uid: str
    user_name: Optional[str] = None
    identifier: Optional[str] = None
    message: str
    beep_count: int   # 1, 2, 3
    beep_ms: int      # beep duration in ms
    led_color: str    # "green", "red", "blue"
    timestamp: str

# User models
class UserBase(BaseModel):
    card_uid: str
    name: str
    identifier: Optional[str] = ""
    department: Optional[str] = "General"
    role: Optional[str] = "Member"
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    identifier: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Attendance Log models
class AttendanceLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    card_uid: str
    timestamp: datetime
    log_type: str
    device_id: str
    note: Optional[str] = None
    user_name: Optional[str] = None
    identifier: Optional[str] = None

    class Config:
        from_attributes = True

# Stats model
class DashboardStats(BaseModel):
    total_users: int
    today_attendees: int
    currently_in: int
    today_scans: int
    unregistered_scans: int
