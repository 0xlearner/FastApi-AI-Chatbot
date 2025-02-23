from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PDFBase(BaseModel):
    filename: str
    file_path: str


class PDFCreate(PDFBase):
    pass


class PDF(PDFBase):
    id: int
    file_id: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True  # for SQLAlchemy models compatibility
