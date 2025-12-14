"""
Database configuration and models using SQLAlchemy.
Supports PostgreSQL, MySQL, and SQLite for flexibility.
"""
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Optional
from datetime import datetime, timezone
import os
from pathlib import Path
from dotenv import load_dotenv
from app.config import settings

# Load .env file from project root
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    # Try loading from current directory
    load_dotenv()

Base = declarative_base()


class FileMetadata(Base):
    """Database model for file metadata."""
    __tablename__ = "file_metadata"
    
    id = Column(String, primary_key=True)
    s3_url = Column(String, nullable=True)
    s3_key = Column(String, nullable=True)
    job_id = Column(String, nullable=True)
    file_metadata = Column("metadata", JSON, nullable=True, default=dict)  # Column name is 'metadata', attribute is 'file_metadata' to avoid SQLAlchemy conflict
    video_width = Column(Integer, nullable=True)
    video_height = Column(Integer, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    thumbnail_key = Column(String, nullable=True)
    playlist_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True, index=True)  # Owner of the video
    is_public = Column(Integer, default=0)  # 0 = private, 1 = public
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Playlist(Base):
    """Database model for playlists."""
    __tablename__ = "playlists"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    publish_status = Column(String, default="private")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class User(Base):
    """Database model for users."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)  # For future use, currently using fixed password
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# Database connection
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """
    Get database URL from environment variable or use default SQLite.
    
    Priority:
    1. DATABASE_URL (if set, uses this directly)
    2. DB_TYPE + individual components (if DB_TYPE is set)
    3. SQLite (default, if nothing is configured)
    """
    # Check for DATABASE_URL first (common for PostgreSQL, MySQL, etc.)
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.strip():
        # Mask password in log for security
        masked_url = db_url
        if "@" in db_url and "://" in db_url:
            parts = db_url.split("@")
            if len(parts) == 2:
                protocol_part = parts[0].split("://")
                if len(protocol_part) == 2:
                    masked_url = f"{protocol_part[0]}://***@{parts[1]}"
        print(f"Using database from DATABASE_URL: {masked_url}")
        return db_url
    
    # Check for individual components
    db_type = os.getenv("DB_TYPE", "").lower().strip()
    
    # If DB_TYPE is explicitly set to something other than sqlite, use it
    if db_type and db_type not in ["sqlite", ""]:
        if db_type == "postgresql" or db_type == "postgres":
            user = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "youtube_dlp")
            db_url = f"postgresql://{user}:***@{host}:{port}/{db_name}"
            print(f"Using PostgreSQL database: {host}:{port}/{db_name}")
            return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        
        elif db_type == "mysql":
            user = os.getenv("DB_USER", "root")
            password = os.getenv("DB_PASSWORD", "")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "3306")
            db_name = os.getenv("DB_NAME", "youtube_dlp")
            db_url = f"mysql+pymysql://{user}:***@{host}:{port}/{db_name}"
            print(f"Using MySQL database: {host}:{port}/{db_name}")
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    
    # Default to SQLite (local file) - no configuration needed
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(backend_dir, "database.sqlite")
    print(f"Using SQLite database (default): {db_path}")
    print("  To use Supabase or other databases, set DATABASE_URL or DB_TYPE in .env file")
    return f"sqlite:///{db_path}"


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        
        # Special handling for SQLite
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            # For PostgreSQL, MySQL, etc.
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,  # Verify connections before using
                echo=False
            )
        
        # Create tables
        Base.metadata.create_all(bind=_engine)
    
    return _engine


def get_session() -> Session:
    """Get database session."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return _SessionLocal()


def init_db():
    """Initialize database (create tables)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")


def close_db():
    """Close database connections."""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None

