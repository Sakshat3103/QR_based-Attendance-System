from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import engine, Base
from routes import auth, sections, students, sessions, attendance

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AttendX API", version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router,       prefix="/api/auth",       tags=["Auth"])
app.include_router(sections.router,   prefix="/api/sections",   tags=["Sections"])
app.include_router(students.router,   prefix="/api/students",   tags=["Students"])
app.include_router(sessions.router,   prefix="/api/sessions",   tags=["Sessions"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])

_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
_static   = os.path.join(_frontend, "static")

if os.path.exists(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")

@app.get("/", include_in_schema=False)
def index(): return FileResponse(os.path.join(_frontend, "index.html"))

@app.get("/attend", include_in_schema=False)
def attend(): return FileResponse(os.path.join(_frontend, "attend.html"))

@app.get("/api/health")
def health(): return {"status": "ok", "app": "AttendX v2.0"}
