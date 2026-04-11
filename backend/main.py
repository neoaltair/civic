import os
import uuid
import json
import shutil
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from sqlalchemy import (
    create_engine, Column, String, Boolean, Integer, Text, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

import bcrypt as _bcrypt
import jwt
from pydantic import BaseModel

# ─── Config ───────────────────────────────────────────────────────────────────

SECRET_KEY   = os.getenv("SECRET_KEY", "civicfix_secret")
ALGORITHM    = os.getenv("ALGORITHM", "HS256")
TOKEN_EXP    = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
DATABASE_URL = "sqlite:///./civic.db"
UPLOADS_DIR  = os.path.join(os.path.dirname(__file__), "uploads")
BASE_URL     = "http://localhost:8000"

os.makedirs(UPLOADS_DIR, exist_ok=True)

# ─── DB Setup ─────────────────────────────────────────────────────────────────

engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()

# ─── Models ───────────────────────────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name          = Column(String, nullable=False)
    email         = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role          = Column(String, default="citizen")   # citizen | admin
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ComplaintModel(Base):
    __tablename__ = "complaints"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email  = Column(String, nullable=False, index=True)
    user_name   = Column(String, nullable=False)
    category    = Column(String, nullable=False)
    location    = Column(String, nullable=False)
    description = Column(Text,   nullable=False)
    is_public   = Column(Boolean, default=True)
    status      = Column(String, default="Pending")
    remarks     = Column(Text,   nullable=True)
    lat         = Column(String, nullable=True)
    lng         = Column(String, nullable=True)
    image_name  = Column(String, nullable=True)
    image_url   = Column(String, nullable=True)   # NEW: full URL to uploaded image
    upvotes     = Column(Integer, default=0)
    upvoted_by  = Column(Text,   default="[]")    # JSON list of emails
    timestamp   = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CommentModel(Base):
    __tablename__ = "comments"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String, nullable=False, index=True)
    user_email   = Column(String, nullable=False)
    user_name    = Column(String, nullable=False)
    text         = Column(Text, nullable=False)
    timestamp    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AnnouncementModel(Base):
    __tablename__ = "announcements"
    id        = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title     = Column(String, nullable=False)
    content   = Column(Text,   nullable=False)
    author    = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EventModel(Base):
    __tablename__ = "events"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title       = Column(String, nullable=False)
    description = Column(Text,   nullable=False)
    date        = Column(String, nullable=False)
    location    = Column(String, nullable=False)
    attendees   = Column(Text, default="[]")      # JSON list of emails
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name:     str
    email:    str
    password: str
    role:     str = "citizen"

class LoginBody(BaseModel):
    email:    str
    password: str

class PatchComplaintBody(BaseModel):
    status:  Optional[str] = None
    remarks: Optional[str] = None

class AnnouncementBody(BaseModel):
    title:   str
    content: str

class EventBody(BaseModel):
    title:       str
    description: str
    date:        str
    location:    str

class CommentBody(BaseModel):
    text: str

class PatchProfileBody(BaseModel):
    name:     Optional[str] = None
    password: Optional[str] = None

# ─── Helpers ──────────────────────────────────────────────────────────────────

bearer_sec = HTTPBearer()

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXP)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_sec),
    db:    Session                       = Depends(get_db)
) -> UserModel:
    payload = decode_token(creds.credentials)
    user = db.query(UserModel).filter(UserModel.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def admin_required(user: UserModel = Depends(current_user)) -> UserModel:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ─── Serialisers ──────────────────────────────────────────────────────────────

def serialize_complaint(c: ComplaintModel) -> dict:
    upvoted_by = json.loads(c.upvoted_by or "[]")
    coordinates = None
    if c.lat and c.lng:
        coordinates = {"lat": float(c.lat), "lng": float(c.lng)}
    return {
        "id":          c.id,
        "userEmail":   c.user_email,
        "userName":    c.user_name,
        "category":    c.category,
        "location":    c.location,
        "description": c.description,
        "isPublic":    c.is_public,
        "status":      c.status,
        "remarks":     c.remarks,
        "imageName":   c.image_name,
        "imageUrl":    c.image_url,
        "upvotes":     c.upvotes,
        "upvotedBy":   upvoted_by,
        "coordinates": coordinates,
        "timestamp":   c.timestamp.isoformat() if c.timestamp else None,
    }

def serialize_announcement(a: AnnouncementModel) -> dict:
    return {
        "id":        a.id,
        "title":     a.title,
        "content":   a.content,
        "author":    a.author,
        "timestamp": a.timestamp.isoformat() if a.timestamp else None,
    }

def serialize_event(e: EventModel) -> dict:
    return {
        "id":          e.id,
        "title":       e.title,
        "description": e.description,
        "date":        e.date,
        "location":    e.location,
        "attendees":   json.loads(e.attendees or "[]"),
        "createdAt":   e.created_at.isoformat() if e.created_at else None,
    }

def serialize_comment(c: CommentModel) -> dict:
    return {
        "id":          c.id,
        "complaintId": c.complaint_id,
        "userEmail":   c.user_email,
        "userName":    c.user_name,
        "text":        c.text,
        "timestamp":   c.timestamp.isoformat() if c.timestamp else None,
    }

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="CivicFix API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files as static
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(UserModel).filter(UserModel.email == "admin@civic.com").first()
        if not existing:
            admin = UserModel(
                name          = "Admin User",
                email         = "admin@civic.com",
                password_hash = hash_password("admin"),
                role          = "admin",
            )
            db.add(admin)
            db.commit()
            print("✅ Admin seeded: admin@civic.com / admin")
    finally:
        db.close()

# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.post("/auth/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    if db.query(UserModel).filter(UserModel.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = UserModel(
        name          = body.name,
        email         = body.email,
        password_hash = hash_password(body.password),
        role          = body.role,
    )
    db.add(user)
    db.commit()
    return {"message": "Registration successful"}

@app.post("/auth/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "name":  user.name,
            "email": user.email,
            "role":  user.role,
        }
    }

@app.get("/auth/me")
def me(user: UserModel = Depends(current_user)):
    return {"name": user.name, "email": user.email, "role": user.role}

# ─── User Profile ─────────────────────────────────────────────────────────────

@app.get("/users/me/profile")
def get_profile(user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    total = db.query(ComplaintModel).filter(ComplaintModel.user_email == user.email).count()
    resolved = db.query(ComplaintModel).filter(
        ComplaintModel.user_email == user.email,
        ComplaintModel.status == "Resolved"
    ).count()
    return {
        "name":               user.name,
        "email":              user.email,
        "role":               user.role,
        "createdAt":          user.created_at.isoformat() if user.created_at else None,
        "totalComplaints":    total,
        "resolvedComplaints": resolved,
    }

@app.patch("/users/me/profile")
def update_profile(body: PatchProfileBody, user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    if body.name:
        user.name = body.name
        # also update session token sub stays same (email), but name changes
    if body.password:
        user.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return {"name": user.name, "email": user.email, "role": user.role}

# ─── Complaints ───────────────────────────────────────────────────────────────

@app.get("/complaints")
def get_complaints(user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        complaints = db.query(ComplaintModel).all()
    else:
        complaints = db.query(ComplaintModel).filter(ComplaintModel.user_email == user.email).all()
    return [serialize_complaint(c) for c in complaints]

@app.get("/complaints/public")
def get_public_complaints(db: Session = Depends(get_db)):
    complaints = db.query(ComplaintModel).filter(ComplaintModel.is_public == True).all()
    return [serialize_complaint(c) for c in complaints]

@app.get("/complaints/{complaint_id}")
def get_complaint(complaint_id: str, user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    c = db.query(ComplaintModel).filter(ComplaintModel.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if user.role != "admin" and c.user_email != user.email and not c.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    return serialize_complaint(c)

@app.post("/complaints", status_code=201)
async def create_complaint(
    category:    str          = Form(...),
    location:    str          = Form(...),
    description: str          = Form(...),
    isPublic:    str          = Form("true"),
    lat:         Optional[str] = Form(None),
    lng:         Optional[str] = Form(None),
    image:       Optional[UploadFile] = File(None),
    user:        UserModel    = Depends(current_user),
    db:          Session      = Depends(get_db),
):
    image_name = None
    image_url  = None

    if image and image.filename:
        ext        = os.path.splitext(image.filename)[1]
        unique_name = f"{uuid.uuid4()}{ext}"
        save_path   = os.path.join(UPLOADS_DIR, unique_name)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        image_name = unique_name
        image_url  = f"{BASE_URL}/uploads/{unique_name}"

    c = ComplaintModel(
        user_email  = user.email,
        user_name   = user.name,
        category    = category,
        location    = location,
        description = description,
        is_public   = isPublic.lower() in ("true", "1", "yes"),
        lat         = lat or None,
        lng         = lng or None,
        image_name  = image_name,
        image_url   = image_url,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return serialize_complaint(c)

@app.patch("/complaints/{complaint_id}")
def update_complaint(
    complaint_id: str,
    body: PatchComplaintBody,
    admin: UserModel = Depends(admin_required),
    db: Session = Depends(get_db)
):
    c = db.query(ComplaintModel).filter(ComplaintModel.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if body.status is not None:
        c.status = body.status
    if body.remarks is not None:
        c.remarks = body.remarks
    db.commit()
    db.refresh(c)
    return serialize_complaint(c)

@app.post("/complaints/{complaint_id}/upvote")
def upvote_complaint(complaint_id: str, user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    c = db.query(ComplaintModel).filter(ComplaintModel.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    upvoted_by = json.loads(c.upvoted_by or "[]")
    if user.email in upvoted_by:
        upvoted_by.remove(user.email)
        c.upvotes = max(0, c.upvotes - 1)
    else:
        upvoted_by.append(user.email)
        c.upvotes += 1
    c.upvoted_by = json.dumps(upvoted_by)
    db.commit()
    db.refresh(c)
    return serialize_complaint(c)

# ─── Comments ────────────────────────────────────────────────────────────────

@app.get("/complaints/{complaint_id}/comments")
def get_comments(complaint_id: str, user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    comments = db.query(CommentModel).filter(CommentModel.complaint_id == complaint_id).all()
    return [serialize_comment(c) for c in comments]

@app.post("/complaints/{complaint_id}/comments", status_code=201)
def add_comment(complaint_id: str, body: CommentBody, user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    complaint = db.query(ComplaintModel).filter(ComplaintModel.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    comment = CommentModel(
        complaint_id = complaint_id,
        user_email   = user.email,
        user_name    = user.name,
        text         = body.text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return serialize_comment(comment)

# ─── Announcements ────────────────────────────────────────────────────────────

@app.get("/announcements")
def get_announcements(db: Session = Depends(get_db)):
    items = db.query(AnnouncementModel).all()
    return [serialize_announcement(a) for a in items]

@app.post("/announcements", status_code=201)
def create_announcement(body: AnnouncementBody, admin: UserModel = Depends(admin_required), db: Session = Depends(get_db)):
    a = AnnouncementModel(title=body.title, content=body.content, author=admin.name)
    db.add(a)
    db.commit()
    db.refresh(a)
    return serialize_announcement(a)

@app.delete("/announcements/{announcement_id}", status_code=204)
def delete_announcement(announcement_id: str, admin: UserModel = Depends(admin_required), db: Session = Depends(get_db)):
    a = db.query(AnnouncementModel).filter(AnnouncementModel.id == announcement_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Announcement not found")
    db.delete(a)
    db.commit()

# ─── Events ───────────────────────────────────────────────────────────────────

@app.get("/events")
def get_events(db: Session = Depends(get_db)):
    events = db.query(EventModel).all()
    return [serialize_event(e) for e in events]

@app.post("/events", status_code=201)
def create_event(body: EventBody, admin: UserModel = Depends(admin_required), db: Session = Depends(get_db)):
    e = EventModel(
        title       = body.title,
        description = body.description,
        date        = body.date,
        location    = body.location,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return serialize_event(e)

@app.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: str, admin: UserModel = Depends(admin_required), db: Session = Depends(get_db)):
    e = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(e)
    db.commit()

@app.post("/events/{event_id}/join")
def join_event(event_id: str, user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    e = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    attendees = json.loads(e.attendees or "[]")
    if user.email not in attendees:
        attendees.append(user.email)
        e.attendees = json.dumps(attendees)
        db.commit()
        db.refresh(e)
    return serialize_event(e)

@app.post("/events/{event_id}/leave")
def leave_event(event_id: str, user: UserModel = Depends(current_user), db: Session = Depends(get_db)):
    e = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    attendees = json.loads(e.attendees or "[]")
    if user.email in attendees:
        attendees.remove(user.email)
        e.attendees = json.dumps(attendees)
        db.commit()
        db.refresh(e)
    return serialize_event(e)

# ─── Admin Stats ──────────────────────────────────────────────────────────────

@app.get("/admin/stats")
def admin_stats(admin: UserModel = Depends(admin_required), db: Session = Depends(get_db)):
    total_users      = db.query(UserModel).count()
    total_complaints = db.query(ComplaintModel).count()
    pending          = db.query(ComplaintModel).filter(ComplaintModel.status == "Pending").count()
    resolved         = db.query(ComplaintModel).filter(ComplaintModel.status == "Resolved").count()
    in_progress      = db.query(ComplaintModel).filter(ComplaintModel.status == "In Progress").count()
    return {
        "totalUsers":      total_users,
        "totalComplaints": total_complaints,
        "pending":         pending,
        "resolved":        resolved,
        "inProgress":      in_progress,
    }
