from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models, schemas
from middleware.auth_middleware import get_current_professor

router = APIRouter()


@router.get("/", response_model=List[schemas.SectionOut])
def list_sections(db: Session = Depends(get_db), professor=Depends(get_current_professor)):
    sections = db.query(models.Section).filter(
        models.Section.professor_id == professor.id
    ).order_by(models.Section.created_at.desc()).all()
    result = []
    for s in sections:
        out = schemas.SectionOut.model_validate(s)
        out.student_count = len(s.students)
        result.append(out)
    return result


@router.post("/", response_model=schemas.SectionOut, status_code=201)
def create_section(body: schemas.SectionCreate, db: Session = Depends(get_db), professor=Depends(get_current_professor)):
    existing = db.query(models.Section).filter(
        models.Section.professor_id == professor.id,
        models.Section.name == body.name.strip(),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Section '{body.name}' already exists.")
    s = models.Section(professor_id=professor.id, name=body.name.strip(), course=body.course.strip(), year_sem=body.year_sem)
    db.add(s); db.commit(); db.refresh(s)
    out = schemas.SectionOut.model_validate(s); out.student_count = 0; return out


@router.post("/get-or-create", response_model=schemas.SectionOut)
def get_or_create_section(body: schemas.SectionCreate, db: Session = Depends(get_db), professor=Depends(get_current_professor)):
    existing = db.query(models.Section).filter(
        models.Section.professor_id == professor.id,
        models.Section.name == body.name.strip(),
    ).first()
    if existing:
        out = schemas.SectionOut.model_validate(existing); out.student_count = len(existing.students); return out
    s = models.Section(professor_id=professor.id, name=body.name.strip(), course=body.course.strip() if body.course else body.name.strip(), year_sem=body.year_sem)
    db.add(s); db.commit(); db.refresh(s)
    out = schemas.SectionOut.model_validate(s); out.student_count = 0; return out


@router.delete("/{section_id}", status_code=204)
def delete_section(section_id: int, db: Session = Depends(get_db), professor=Depends(get_current_professor)):
    s = db.query(models.Section).filter(models.Section.id == section_id, models.Section.professor_id == professor.id).first()
    if not s: raise HTTPException(status_code=404, detail="Section not found.")
    db.delete(s); db.commit()
