from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import shutil

DB_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DB = os.path.abspath(os.path.join(DB_DIR, "..", "attendance.db"))

# Handle Vercel serverless environment (read-only filesystem except /tmp)
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    TMP_DB = "/tmp/attendance.db"
    if not os.path.exists(TMP_DB) and os.path.exists(LOCAL_DB):
        try:
            shutil.copyfile(LOCAL_DB, TMP_DB)
        except Exception:
            pass
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{TMP_DB}"
elif os.environ.get("DATABASE_URL"):
    SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
else:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{LOCAL_DB}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
