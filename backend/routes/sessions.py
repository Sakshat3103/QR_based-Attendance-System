import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from middleware.auth_middleware import get_current_professor

router = APIRouter()

def _now():
    return datetime.utcnow().replace(tzinfo=timezone.utc)

def _expire_stale(db, section_ids):
    now = _now()
    for sid in section_ids:
        for s in db.query(models.QRSession).filter(models.QRSession.section_id==sid, models.QRSession.status==models.SessionStatus.active).all():
            exp = s.expires_at if s.expires_at.tzinfo else s.expires_at.replace(tzinfo=timezone.utc)
            if exp <= now:
                s.status = models.SessionStatus.expired
    db.commit()

@router.get("/", response_model=List[schemas.SessionOut])
def list_sessions(section_id: Optional[int]=Query(None), db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    ids = [s.id for s in professor.sections]
    _expire_stale(db, ids)
    q = db.query(models.QRSession).filter(models.QRSession.section_id.in_(ids))
    if section_id: q = q.filter(models.QRSession.section_id == section_id)
    sessions = q.order_by(models.QRSession.created_at.desc()).all()
    result = []
    for s in sessions:
        out = schemas.SessionOut.model_validate(s)
        out.attend_count = len(s.attendance)
        out.section_name = s.section.name if s.section else ""
        result.append(out)
    return result

@router.post("/", response_model=schemas.SessionOut, status_code=201)
def create_session(body: schemas.SessionCreate, db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    sec = db.query(models.Section).filter(models.Section.id==body.section_id, models.Section.professor_id==professor.id).first()
    if not sec: raise HTTPException(status_code=404, detail="Section not found.")
    db.query(models.QRSession).filter(models.QRSession.section_id==body.section_id, models.QRSession.status==models.SessionStatus.active).update({"status": models.SessionStatus.expired})
    db.commit()
    now = _now()
    session = models.QRSession(section_id=body.section_id, name=body.name.strip(),
        token=secrets.token_urlsafe(32), ttl=body.ttl, expires_at=now+timedelta(minutes=body.ttl),
        status=models.SessionStatus.active, prof_lat=body.prof_lat, prof_lng=body.prof_lng, geo_radius=body.geo_radius)
    db.add(session); db.commit(); db.refresh(session)
    out = schemas.SessionOut.model_validate(session)
    out.attend_count = 0; out.section_name = sec.name
    return out

@router.post("/{session_id}/expire", response_model=schemas.SessionOut)
def expire_session(session_id: int, db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    ids = [s.id for s in professor.sections]
    s = db.query(models.QRSession).filter(models.QRSession.id==session_id, models.QRSession.section_id.in_(ids)).first()
    if not s: raise HTTPException(status_code=404, detail="Session not found.")
    s.status = models.SessionStatus.expired; db.commit(); db.refresh(s)
    out = schemas.SessionOut.model_validate(s)
    out.attend_count = len(s.attendance); out.section_name = s.section.name if s.section else ""
    return out

@router.get("/verify/{token}")
def verify_token(token: str, db: Session=Depends(get_db)):
    now = _now()
    s = db.query(models.QRSession).filter(models.QRSession.token==token).first()
    if not s: raise HTTPException(status_code=404, detail="Invalid QR code token.")
    exp = s.expires_at if s.expires_at.tzinfo else s.expires_at.replace(tzinfo=timezone.utc)
    if exp < now:
        s.status = models.SessionStatus.expired; db.commit()
        raise HTTPException(status_code=410, detail="This QR code has expired. Ask your professor for a new one.")
    if s.status == models.SessionStatus.expired:
        raise HTTPException(status_code=410, detail="This session has been closed.")
    return {"valid": True, "session_id": s.id, "session_name": s.name,
        "section_id": s.section_id, "section_name": s.section.name if s.section else "",
        "expires_at": exp.isoformat(), "ttl": s.ttl,
        "prof_lat": s.prof_lat, "prof_lng": s.prof_lng, "geo_radius": s.geo_radius or 100}
