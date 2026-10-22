import re
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from . import models, schemas

SCAN_COOLDOWN_SECONDS = 8  # Debounce duplicate swipes within 8 seconds

def normalize_uid(raw_uid: str) -> str:
    """Normalize any card UID format (e.g. 'a1:b2:c3:d4' or 'a1 b2') to uppercase hex string."""
    cleaned = re.sub(r'[^A-Fa-f0-9]', '', raw_uid or '')
    return cleaned.upper()

def get_user_by_uid(db: Session, card_uid: str) -> Optional[models.User]:
    clean_uid = normalize_uid(card_uid)
    return db.query(models.User).filter(models.User.card_uid == clean_uid).first()

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 500) -> List[models.User]:
    return db.query(models.User).order_by(models.User.name).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    clean_uid = normalize_uid(user.card_uid)
    db_user = models.User(
        card_uid=clean_uid,
        name=user.name.strip(),
        identifier=user.identifier.strip() if user.identifier else "",
        department=user.department.strip() if user.department else "General",
        role=user.role.strip() if user.role else "Member",
        is_active=user.is_active if user.is_active is not None else True,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_in: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(db_user, field, val)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    db.delete(db_user)
    db.commit()
    return True

def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    return setting.value if setting else default

def set_setting(db: Session, key: str, value: str):
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if not setting:
        setting = models.SystemSetting(key=key, value=value, updated_at=datetime.utcnow())
        db.add(setting)
    else:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    db.commit()

def process_rfid_scan(db: Session, raw_uid: str, device_id: str = "ESP32-READER-01") -> Tuple[schemas.ScanResponse, Optional[dict]]:
    """
    Process an incoming RFID scan from the ESP32.
    Returns:
        (ScanResponse, broadcast_event_dict)
    """
    clean_uid = normalize_uid(raw_uid)
    now = datetime.utcnow()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    if not clean_uid:
        return schemas.ScanResponse(
            success=False,
            status="INVALID",
            card_uid=raw_uid,
            message="Invalid or empty card UID received",
            beep_count=3,
            beep_ms=200,
            led_color="red",
            timestamp=timestamp_str
        ), None

    # Check registration mode setting
    reg_mode = get_setting(db, "registration_mode", "false").lower() == "true"
    # Always remember the last scanned card
    set_setting(db, "last_scanned_uid", clean_uid)

    user = get_user_by_uid(db, clean_uid)

    if not user:
        # Unregistered card
        log_entry = models.AttendanceLog(
            user_id=None,
            card_uid=clean_uid,
            timestamp=now,
            log_type="UNKNOWN",
            device_id=device_id,
            note="Unregistered card scanned"
        )
        db.add(log_entry)
        db.commit()

        event = {
            "type": "SCAN_EVENT",
            "status": "UNREGISTERED",
            "card_uid": clean_uid,
            "user_name": "Unregistered Card",
            "identifier": "-",
            "department": "-",
            "log_type": "UNKNOWN",
            "timestamp": timestamp_str,
            "registration_mode": reg_mode
        }

        return schemas.ScanResponse(
            success=False,
            status="UNREGISTERED",
            card_uid=clean_uid,
            message="Card not registered! Tap 'Register' on dashboard.",
            beep_count=3,
            beep_ms=300,
            led_color="red",
            timestamp=timestamp_str
        ), event

    if not user.is_active:
        return schemas.ScanResponse(
            success=False,
            status="DEACTIVATED",
            card_uid=clean_uid,
            user_name=user.name,
            identifier=user.identifier,
            message=f"User {user.name} is deactivated",
            beep_count=3,
            beep_ms=400,
            led_color="red",
            timestamp=timestamp_str
        ), None

    # Check debounce / cooldown with last scan for this user
    last_log = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.user_id == user.id
    ).order_by(desc(models.AttendanceLog.timestamp)).first()

    if last_log and (now - last_log.timestamp).total_seconds() < SCAN_COOLDOWN_SECONDS:
        return schemas.ScanResponse(
            success=True,
            status="COOLDOWN",
            card_uid=clean_uid,
            user_name=user.name,
            identifier=user.identifier,
            message=f"Hello {user.name}! Already recorded just now.",
            beep_count=1,
            beep_ms=80,
            led_color="blue",
            timestamp=timestamp_str
        ), None

    # Determine toggle: If last log was CHECK_IN on the same calendar day, toggle to CHECK_OUT, otherwise CHECK_IN
    # We check if today already has a CHECK_IN without matching CHECK_OUT
    today_start = datetime.combine(now.date(), time.min)
    today_logs = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.user_id == user.id,
        models.AttendanceLog.timestamp >= today_start
    ).order_by(desc(models.AttendanceLog.timestamp)).all()

    if today_logs and today_logs[0].log_type == "CHECK_IN":
        next_type = "CHECK_OUT"
        msg = f"Goodbye, {user.name}! Checked OUT."
        beeps = 2
    else:
        next_type = "CHECK_IN"
        msg = f"Welcome, {user.name}! Checked IN."
        beeps = 1

    # Record log
    new_log = models.AttendanceLog(
        user_id=user.id,
        card_uid=clean_uid,
        timestamp=now,
        log_type=next_type,
        device_id=device_id,
        note=f"{next_type} recorded successfully"
    )
    db.add(new_log)
    db.commit()

    event = {
        "type": "SCAN_EVENT",
        "status": "SUCCESS",
        "card_uid": clean_uid,
        "user_name": user.name,
        "identifier": user.identifier,
        "department": user.department,
        "role": user.role,
        "log_type": next_type,
        "timestamp": timestamp_str
    }

    return schemas.ScanResponse(
        success=True,
        status=next_type,
        card_uid=clean_uid,
        user_name=user.name,
        identifier=user.identifier,
        message=msg,
        beep_count=beeps,
        beep_ms=150,
        led_color="green",
        timestamp=timestamp_str
    ), event

def get_attendance_logs(
    db: Session,
    target_date: Optional[date] = None,
    user_id: Optional[int] = None,
    limit: int = 200
) -> List[schemas.AttendanceLogOut]:
    query = db.query(
        models.AttendanceLog,
        models.User.name.label("user_name"),
        models.User.identifier.label("identifier")
    ).outerjoin(models.User, models.AttendanceLog.user_id == models.User.id)

    if target_date:
        start_dt = datetime.combine(target_date, time.min)
        end_dt = datetime.combine(target_date, time.max)
        query = query.filter(models.AttendanceLog.timestamp.between(start_dt, end_dt))

    if user_id:
        query = query.filter(models.AttendanceLog.user_id == user_id)

    records = query.order_by(desc(models.AttendanceLog.timestamp)).limit(limit).all()

    result = []
    for log, name, ident in records:
        out = schemas.AttendanceLogOut(
            id=log.id,
            user_id=log.user_id,
            card_uid=log.card_uid,
            timestamp=log.timestamp,
            log_type=log.log_type,
            device_id=log.device_id,
            note=log.note,
            user_name=name or "Unregistered Card",
            identifier=ident or "-"
        )
        result.append(out)
    return result

def get_stats(db: Session) -> schemas.DashboardStats:
    total_users = db.query(models.User).filter(models.User.is_active == True).count()
    
    today_start = datetime.combine(datetime.utcnow().date(), time.min)

    today_logs = db.query(models.AttendanceLog).filter(
        models.AttendanceLog.timestamp >= today_start
    ).all()

    today_scans = len(today_logs)
    unregistered_scans = sum(1 for l in today_logs if l.log_type == "UNKNOWN")
    
    unique_attendee_ids = {l.user_id for l in today_logs if l.user_id is not None}
    today_attendees = len(unique_attendee_ids)

    # Calculate currently in building: for each user who scanned today, is their latest log today CHECK_IN?
    currently_in = 0
    for uid in unique_attendee_ids:
        user_today_logs = [l for l in today_logs if l.user_id == uid]
        if user_today_logs:
            latest = max(user_today_logs, key=lambda l: l.timestamp)
            if latest.log_type == "CHECK_IN":
                currently_in += 1

    return schemas.DashboardStats(
        total_users=total_users,
        today_attendees=today_attendees,
        currently_in=currently_in,
        today_scans=today_scans,
        unregistered_scans=unregistered_scans
    )
