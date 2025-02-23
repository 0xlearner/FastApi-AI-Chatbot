from sqlalchemy.orm import Session
from app.db.session import engine
from app.models.domain.user import Base as UserBase
from app.models.domain.pdf import Base as PDFBase
import os
from app.core.config import settings


def init_db():
    # Create the uploads directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Create all tables
    UserBase.metadata.create_all(bind=engine)
    PDFBase.metadata.create_all(bind=engine)
