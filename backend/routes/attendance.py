import io, csv, math
from datetime import timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
import models, schemas
from middleware.auth_middleware import get_current_professor

router = APIRouter()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1,p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2)-float(lat1))
    dl = math.radians(float(lon2)-float(lon1))
    a  = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

@router.post("/submit", status_code=201)
def submit_attendance(body: schemas.AttendanceSubmit, db: Session=Depends(get_db)):
    from datetime import datetime
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    layers = []

    # Layer 1: Token
    session = db.query(models.QRSession).filter(models.QRSession.token==body.token.strip()).first()
    if not session: raise HTTPException(status_code=404, detail="LAYER_1_FAIL: Invalid QR token.")
    exp = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
    if exp < now:
        session.status = models.SessionStatus.expired; db.commit()
        raise HTTPException(status_code=410, detail="LAYER_1_FAIL: QR code has expired.")
    if session.status == models.SessionStatus.expired:
        raise HTTPException(status_code=410, detail="LAYER_1_FAIL: Session is closed.")
    layers.append("token")

    # Layer 2: Registration
    student = db.query(models.Student).filter(
        models.Student.reg_number==body.reg_number.upper().strip(),
        models.Student.section_id==session.section_id).first()
    if not student: raise HTTPException(status_code=404, detail="LAYER_2_FAIL: Registration number not found in this section.")
    layers.append("reg")

    # Layer 3: Duplicate
    if db.query(models.Attendance).filter(models.Attendance.student_id==student.id, models.Attendance.session_id==session.id).first():
        raise HTTPException(status_code=409, detail="LAYER_3_FAIL: Attendance already marked for this session.")
    layers.append("duplicate")

    # Layer 5: GPS proximity (if professor GPS is set)
    if session.prof_lat and session.prof_lng and body.latitude and body.longitude:
        try:
            dist = haversine(session.prof_lat, session.prof_lng, body.latitude, body.longitude)
            radius = session.geo_radius or 100
            if dist > radius:
                raise HTTPException(status_code=403,
                    detail=f"LAYER_5_FAIL: You are {int(dist)}m away. Must be within {radius}m of the classroom.")
            layers.append("gps")
        except HTTPException: raise
        except: layers.append("gps")
    elif body.latitude and body.longitude:
        layers.append("gps")

    record = models.Attendance(student_id=student.id, session_id=session.id,
        layers_passed=",".join(layers), latitude=body.latitude, longitude=body.longitude)
    db.add(record)
    try:
        db.commit(); db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="LAYER_3_FAIL: Attendance already marked.")

    return {"success": True, "message": "Attendance marked successfully!",
        "student_name": student.name, "reg_number": student.reg_number,
        "session_name": session.name,
        "section_name": session.section.name if session.section else "",
        "timestamp": record.timestamp.isoformat(), "layers": layers}

@router.get("/", response_model=List[schemas.AttendanceOut])
def list_attendance(section_id: Optional[int]=Query(None), session_id: Optional[int]=Query(None),
    db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    ids = [s.id for s in professor.sections]
    q = db.query(models.Attendance).join(models.Attendance.student).join(models.Student.section).filter(models.Section.id.in_(ids))
    if section_id: q = q.filter(models.Student.section_id==section_id)
    if session_id: q = q.filter(models.Attendance.session_id==session_id)
    records = q.order_by(models.Attendance.timestamp.desc()).all()
    result = []
    for r in records:
        out = schemas.AttendanceOut.model_validate(r)
        out.student_name = r.student.name if r.student else ""
        out.reg_number   = r.student.reg_number if r.student else ""
        out.section_name = r.student.section.name if r.student and r.student.section else ""
        out.session_name = r.session.name if r.session else ""
        result.append(out)
    return result

@router.get("/analytics/summary")
def analytics_summary(db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    ids = [s.id for s in professor.sections]
    total_students = db.query(models.Student).filter(models.Student.section_id.in_(ids)).count()
    total_sessions = db.query(models.QRSession).filter(models.QRSession.section_id.in_(ids)).count()
    total_records  = db.query(models.Attendance).join(models.Attendance.student).filter(models.Student.section_id.in_(ids)).count()
    overall_pct = round((total_records/(total_students*total_sessions))*100,1) if total_students and total_sessions else 0.0
    students = db.query(models.Student).filter(models.Student.section_id.in_(ids)).all()
    sec_sessions = {sid: db.query(models.QRSession).filter(models.QRSession.section_id==sid).count() for sid in ids}
    above_75 = sum(1 for s in students if (len(s.attendance)/sec_sessions.get(s.section_id,1)*100 if sec_sessions.get(s.section_id) else 0) >= 75)
    section_data = []
    for sec in professor.sections:
        sc = sec_sessions.get(sec.id, 0)
        ss = len(sec.students)
        sr = db.query(models.Attendance).join(models.Attendance.student).filter(models.Student.section_id==sec.id).count()
        section_data.append({"id":sec.id,"name":sec.name,"course":sec.course,"student_count":ss,"session_count":sc,"record_count":sr,
            "attendance_pct": round((sr/(ss*sc))*100,1) if ss and sc else 0})
    recent = db.query(models.QRSession).filter(models.QRSession.section_id.in_(ids)).order_by(models.QRSession.created_at.desc()).limit(10).all()
    trend = []
    for ses in reversed(recent):
        cnt = len(ses.attendance)
        tot = db.query(models.Student).filter(models.Student.section_id==ses.section_id).count()
        trend.append({"session_name":ses.name,"attend_count":cnt,"total_students":tot,"pct":round((cnt/tot)*100,1) if tot else 0,"created_at":ses.created_at.isoformat()})
    return {"total_students":total_students,"total_sections":len(ids),"total_sessions":total_sessions,
        "total_records":total_records,"overall_pct":overall_pct,"students_above_75":above_75,
        "students_below_75":total_students-above_75,"section_data":section_data,"session_trend":trend,
        "professor_name": professor.name, "professor_dept": professor.department or ""}


@router.get("/report/{session_id}")
def get_session_report(
    session_id: int,
    db:         Session           = Depends(get_db),
    professor:  models.Professor  = Depends(get_current_professor),
):
    """
    Returns full present/absent report for a specific session.
    Includes every student in the section — not just those who attended.
    """
    prof_section_ids = [s.id for s in professor.sections]

    session = db.query(models.QRSession).filter(
        models.QRSession.id         == session_id,
        models.QRSession.section_id.in_(prof_section_ids),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    section  = session.section
    students = db.query(models.Student).filter(
        models.Student.section_id == session.section_id
    ).order_by(models.Student.name).all()

    attendance_map = {
        a.student_id: a
        for a in db.query(models.Attendance).filter(
            models.Attendance.session_id == session_id
        ).all()
    }

    rows = []
    for s in students:
        rec     = attendance_map.get(s.id)
        present = rec is not None
        ts      = rec.timestamp.strftime("%Y-%m-%d %H:%M:%S") if rec and rec.timestamp else "—"
        rows.append({
            "name":      s.name,
            "reg":       s.reg_number,
            "section":   section.name if section else "",
            "status":    "Present" if present else "Absent",
            "timestamp": ts,
            "layers":    rec.layers_passed if rec else "—",
        })

    present_count = sum(1 for r in rows if r["status"] == "Present")
    absent_count  = len(rows) - present_count
    rate          = round((present_count / len(rows)) * 100, 1) if rows else 0

    return {
        "session_name":    session.name,
        "section_name":    section.name if section else "",
        "professor_name":  professor.name,
        "professor_dept":  professor.department or "",
        "created_at":      session.created_at.isoformat() if session.created_at else "",
        "total":           len(rows),
        "present":         present_count,
        "absent":          absent_count,
        "rate":            rate,
        "rows":            rows,
    }
