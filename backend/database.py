import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_default_db = "sqlite:///" + os.path.join(_base_dir, "attendx.db")
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
