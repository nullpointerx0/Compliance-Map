import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base

# Ensure database directory exists for SQLite
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    # Extract path and make it absolute to prevent directory errors
    db_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

# Create SQLAlchemy engine
# connect_args={"check_same_thread": False} is required only for SQLite
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Creates all tables in the SQLite database as defined in the models.
    """
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    Context generator for database sessions to use in FastAPI endpoints
    or operational scripts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
