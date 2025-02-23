from contextlib import contextmanager
from app.db.session import SessionLocal


@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
