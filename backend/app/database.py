"""
SQLAlchemy database engine, session, and base model setup.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# pool_pre_ping=True: validates the connection before use — critical for cloud
# databases (Azure PostgreSQL) that close idle TCP connections after ~5 minutes.
# pool_recycle=1800: force-recycle connections every 30 min regardless of activity.
engine = create_engine(
    settings.db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
