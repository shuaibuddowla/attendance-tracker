import os
import csv
import io
import json
from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .database import engine, get_db

# Create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ESP32 RFID Attendance Tracker", version="1.0.0")

# CORS for local network devices and development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "..", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "..", "templates")

try:
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR, exist_ok=True)
    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
except Exception:
    pass

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# WebSocket Connection Manager for Real-time Dashboard Updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

# Pre-populate sample test users if table is empty
def seed_sample_users():
    db = next(get_db())
    try:
        if db.query(models.User).count() == 0:
            samples = [
                models.User(
                    card_uid="A1B2C3D4",
                    name="Alex Mercer",
                    identifier="EMP-1001",
                    department="Engineering",
                    role="Developer",
                    created_at=datetime.utcnow()
                ),
                models.User(
                    card_uid="E5F67890",
                    name="Sarah Connor",
                    identifier="EMP-1002",
                    department="Cybersecurity",
                    role="Security Lead",
                    created_at=datetime.utcnow()
                ),
                models.User(
                    card_uid="11223344",
                    name="David Kim",
                    identifier="STU-504",
                    department="Robotics Lab",
                    role="Student Researcher",
                    created_at=datetime.utcnow()
                )
            ]
            db.add_all(samples)
            db.commit()
    finally:
        db.close()

seed_sample_users()


# Web UI Route
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open(os.path.join(TEMPLATES_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# WebSocket Endpoint for Live Scan Events
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; clients can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# RFID Scan Endpoint (Called by ESP32 via HTTP POST)
@app.post("/api/scan", response_model=schemas.ScanResponse)
async def rfid_scan(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    """
    Main webhook invoked by ESP32 when an RFID card is tapped.
    Returns status, beep count, and LED indicator back to the ESP32.
    Broadcasts real-time events to connected web browsers via WebSocket.
    """
    response, event = crud.process_rfid_scan(db, payload.card_uid, payload.device_id or "ESP32-READER-01")

    if event:
        # Include updated dashboard stats in the broadcast
        stats = crud.get_stats(db)
        event["stats"] = stats.model_dump()
        await manager.broadcast(event)

    return response


# Simulator endpoint (lets user test the system directly from the browser without ESP32)
@app.post("/api/simulate-scan")
async def simulate_scan(payload: schemas.ScanRequest, db: Session = Depends(get_db)):
    return await rfid_scan(payload, db)


# Users Management API
@app.get("/api/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return crud.get_users(db)


@app.post("/api/users", response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    clean_uid = crud.normalize_uid(user.card_uid)
    existing = crud.get_user_by_uid(db, clean_uid)
    if existing:
        raise HTTPException(status_code=400, detail=f"Card UID '{clean_uid}' is already assigned to {existing.name}.")
    
    new_user = crud.create_user(db, user)
    
    # Broadcast user update event
    stats = crud.get_stats(db)
    await manager.broadcast({
        "type": "USER_CREATED",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "card_uid": new_user.card_uid
        },
        "stats": stats.model_dump()
    })
    return new_user


@app.get("/api/users/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/api/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, user_in: schemas.UserUpdate, db: Session = Depends(get_db)):
    updated = crud.update_user(db, user_id, user_in)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    success = crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    stats = crud.get_stats(db)
    await manager.broadcast({"type": "USER_DELETED", "stats": stats.model_dump()})
    return {"success": True, "message": "User deleted"}


# Attendance Logs API
@app.get("/api/attendance", response_model=List[schemas.AttendanceLogOut])
def get_attendance(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user_id: Optional[int] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    parsed_date = None
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    return crud.get_attendance_logs(db, target_date=parsed_date, user_id=user_id, limit=limit)


@app.get("/api/attendance/export")
def export_attendance_csv(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    parsed_date = None
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    logs = crud.get_attendance_logs(db, target_date=parsed_date, limit=5000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log ID", "Card UID", "User Name", "ID / Roll No", "Type", "Timestamp (UTC)", "Device", "Note"])
    
    for l in logs:
        writer.writerow([
            l.id,
            l.card_uid,
            l.user_name,
            l.identifier,
            l.log_type,
            l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            l.device_id,
            l.note or ""
        ])
    
    output.seek(0)
    filename = f"attendance_{target_date or 'all'}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Dashboard Statistics API
@app.get("/api/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    return crud.get_stats(db)


# System Settings / Last Scanned Card API
@app.get("/api/system/last-scanned")
def get_last_scanned(db: Session = Depends(get_db)):
    last_uid = crud.get_setting(db, "last_scanned_uid", "")
    is_registered = bool(crud.get_user_by_uid(db, last_uid)) if last_uid else False
    return {
        "card_uid": last_uid,
        "is_registered": is_registered
    }
