"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

TEACHERS_FILE = current_dir / "teachers.json"
TEACHER_SESSION_COOKIE = "teacher_session"
TEACHER_SESSION_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000
teacher_sessions: dict[str, tuple[str, float]] = {}


class TeacherLogin(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


def get_teacher_username(request: Request) -> str | None:
    session_token = request.cookies.get(TEACHER_SESSION_COOKIE)
    if session_token is None:
        return None

    session = teacher_sessions.get(session_token)
    if session is None:
        return None

    username, expires_at = session
    if expires_at <= time.time():
        del teacher_sessions[session_token]
        return None
    return username


def require_teacher(request: Request) -> str:
    username = get_teacher_username(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher sign-in required")
    return username


def verify_teacher_credentials(username: str, password: str) -> bool:
    credentials = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    if not isinstance(credentials, dict) or not isinstance(
        credentials.get("teachers"), list
    ):
        raise RuntimeError("teachers.json must contain a 'teachers' list")

    for teacher in credentials["teachers"]:
        if not isinstance(teacher, dict):
            raise RuntimeError("Each teacher entry must be a JSON object")
        teacher_username = teacher.get("username")
        salt_hex = teacher.get("password_salt")
        password_hash = teacher.get("password_hash")
        if not all(isinstance(value, str) for value in (
            teacher_username, salt_hex, password_hash
        )):
            raise RuntimeError(
                "Each teacher needs username, password_salt, and password_hash"
            )

        if teacher_username != username:
            continue
        salt = bytes.fromhex(salt_hex)
        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
        ).hex()
        return hmac.compare_digest(candidate_hash, password_hash)
    return False


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/session")
def get_auth_session(request: Request):
    username = get_teacher_username(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login_teacher(credentials: TeacherLogin, request: Request, response: Response):
    if not verify_teacher_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=401, detail="Invalid teacher username or password"
        )

    now = time.time()
    expired_tokens = [
        token for token, (_, expires_at) in teacher_sessions.items()
        if expires_at <= now
    ]
    for token in expired_tokens:
        del teacher_sessions[token]

    session_token = secrets.token_urlsafe(32)
    teacher_sessions[session_token] = (
        credentials.username, now + TEACHER_SESSION_SECONDS
    )
    response.set_cookie(
        key=TEACHER_SESSION_COOKIE,
        value=session_token,
        max_age=TEACHER_SESSION_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed in successfully", "username": credentials.username}


@app.post("/auth/logout")
def logout_teacher(request: Request, response: Response):
    session_token = request.cookies.get(TEACHER_SESSION_COOKIE)
    if session_token is not None:
        teacher_sessions.pop(session_token, None)
    response.delete_cookie(
        key=TEACHER_SESSION_COOKIE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed out successfully"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
