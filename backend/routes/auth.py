from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from middleware.auth_middleware import hash_password, verify_password, create_access_token, get_current_professor

router = APIRouter()

@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(body: schemas.ProfessorRegister, db: Session = Depends(get_db)):
    if db.query(models.Professor).filter(models.Professor.email == body.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered.")
    prof = models.Professor(name=body.name.strip(), email=body.email.lower().strip(),
        password=hash_password(body.password), department=body.department)
    db.add(prof); db.commit(); db.refresh(prof)
    return schemas.TokenResponse(access_token=create_access_token({"sub": str(prof.id)}),
        professor=schemas.ProfessorOut.model_validate(prof))

@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.ProfessorLogin, db: Session = Depends(get_db)):
    prof = db.query(models.Professor).filter(models.Professor.email == body.email.lower()).first()
    if not prof or not verify_password(body.password, prof.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return schemas.TokenResponse(access_token=create_access_token({"sub": str(prof.id)}),
        professor=schemas.ProfessorOut.model_validate(prof))

@router.get("/me", response_model=schemas.ProfessorOut)
def get_me(professor=Depends(get_current_professor)):
    return schemas.ProfessorOut.model_validate(professor)
