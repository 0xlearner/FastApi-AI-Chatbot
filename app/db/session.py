from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings

# Create SQLite engine with special configuration for SQLite
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    poolclass=StaticPool,  # Better for FastAPI's async nature with SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
