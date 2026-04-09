from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models, schemas
from middleware.auth_middleware import get_current_professor

router = APIRouter()

@router.get("/", response_model=List[schemas.StudentWithAttendance])
def list_students(section_id: Optional[int]=Query(None), search: Optional[str]=Query(None),
    db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    ids = [s.id for s in professor.sections]
    q = db.query(models.Student).filter(models.Student.section_id.in_(ids))
    if section_id: q = q.filter(models.Student.section_id == section_id)
    if search:
        like = f"%{search}%"
        q = q.filter((models.Student.name.ilike(like)) | (models.Student.reg_number.ilike(like)))
    students = q.order_by(models.Student.name).all()
    sec_sessions = {sid: db.query(models.QRSession).filter(models.QRSession.section_id==sid).count() for sid in ids}
    result = []
    for s in students:
        out = schemas.StudentWithAttendance.model_validate(s)
        out.section_name = s.section.name if s.section else ""
        out.attendance_count = len(s.attendance)
        out.total_sessions = sec_sessions.get(s.section_id, 0)
        out.attendance_pct = round((out.attendance_count/out.total_sessions)*100,1) if out.total_sessions else 0.0
        result.append(out)
    return result

@router.post("/", response_model=schemas.StudentOut, status_code=201)
def create_student(body: schemas.StudentCreate, db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    sec = db.query(models.Section).filter(models.Section.id==body.section_id, models.Section.professor_id==professor.id).first()
    if not sec: raise HTTPException(status_code=404, detail="Section not found.")
    if db.query(models.Student).filter(models.Student.reg_number==body.reg_number.upper()).first():
        raise HTTPException(status_code=409, detail=f"Registration number already exists.")
    s = models.Student(section_id=body.section_id, name=body.name.strip(), reg_number=body.reg_number.upper().strip())
    db.add(s); db.commit(); db.refresh(s)
    return schemas.StudentOut.model_validate(s)

@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session=Depends(get_db), professor=Depends(get_current_professor)):
    ids = [s.id for s in professor.sections]
    s = db.query(models.Student).filter(models.Student.id==student_id, models.Student.section_id.in_(ids)).first()
    if not s: raise HTTPException(status_code=404, detail="Student not found.")
    db.delete(s); db.commit()

from fastapi import UploadFile, File
from typing import List as TList
import csv, io


@router.post("/bulk-upload")
async def bulk_upload_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    professor=Depends(get_current_professor)
):
    """
    Upload a CSV/Excel-exported-as-CSV file with columns:
      Name | Registration Number | Section | Course (optional)

    - Creates sections automatically if they don't exist
    - Skips duplicate registration numbers
    - Returns summary of what was added/skipped
    """
    content = await file.read()

    # Try UTF-8, fallback to latin-1 (common in Excel exports)
    try:
        text = content.decode('utf-8-sig')  # utf-8-sig handles Excel BOM
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))

    # Normalize column names (case-insensitive)
    def find_col(row, *names):
        for k in row:
            if k.strip().lower() in [n.lower() for n in names]:
                return row[k].strip()
        return ''

    added   = []
    skipped = []
    errors  = []
    section_cache = {}  # name -> section object

    for i, row in enumerate(reader, start=2):  # start=2 (row 1 is header)
        name    = find_col(row, 'name', 'student name', 'full name', 'student')
        reg     = find_col(row, 'registration number', 'reg number', 'reg no', 'reg', 'registration', 'roll no', 'roll number')
        sec_name = find_col(row, 'section', 'class', 'group')
        course  = find_col(row, 'course', 'subject', 'class name') or sec_name

        if not name or not reg:
            errors.append(f"Row {i}: Missing name or registration number")
            continue

        reg = reg.upper().strip()

        # Skip duplicate reg numbers
        if db.query(models.Student).filter(models.Student.reg_number == reg).first():
            skipped.append(f"{name} ({reg}) — already exists")
            continue

        # Get or create section
        if not sec_name:
            sec_name = 'Default Section'

        if sec_name not in section_cache:
            existing_sec = db.query(models.Section).filter(
                models.Section.professor_id == professor.id,
                models.Section.name == sec_name,
            ).first()
            if existing_sec:
                section_cache[sec_name] = existing_sec
            else:
                new_sec = models.Section(
                    professor_id = professor.id,
                    name         = sec_name,
                    course       = course or sec_name,
                )
                db.add(new_sec)
                db.commit()
                db.refresh(new_sec)
                section_cache[sec_name] = new_sec

        section = section_cache[sec_name]

        student = models.Student(
            section_id = section.id,
            name       = name.strip(),
            reg_number = reg,
        )
        db.add(student)
        try:
            db.commit()
            added.append(f"{name} ({reg}) → {sec_name}")
        except Exception as e:
            db.rollback()
            skipped.append(f"{name} ({reg}) — DB error: {str(e)[:50]}")

    return {
        "success":       True,
        "added_count":   len(added),
        "skipped_count": len(skipped),
        "error_count":   len(errors),
        "added":         added[:50],    # limit to 50 for response size
        "skipped":       skipped[:20],
        "errors":        errors[:20],
    }
