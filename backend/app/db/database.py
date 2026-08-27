import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

IS_TESTING = os.environ.get("TESTING", "false").lower() == "true"

if IS_TESTING:
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_medibot.db")
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
else:
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set. Cannot start without a primary database.")
    if DATABASE_URL.startswith("sqlite"):
        print("WARNING: SQLite is used as the primary database in production. This is NOT recommended for production, but permitted for a demo.")
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
