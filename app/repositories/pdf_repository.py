from sqlalchemy.orm import Session
from app.models.domain.pdf import PDF
from typing import List

class PDFRepository:
    @staticmethod
    async def get_user_pdfs(user_id: int, db: Session) -> List[PDF]:
        """Get all PDFs belonging to a user"""
        return db.query(PDF).filter(PDF.user_id == user_id).all()

    @staticmethod
    async def get_pdf_by_id(file_id: str, db: Session) -> PDF:
        """Get PDF by file_id"""
        return db.query(PDF).filter(PDF.file_id == file_id).first()

    @staticmethod
    def get_pdf_by_filename(filename: str, user_id: int, db: Session) -> PDF:
        """Get PDF by filename and user_id"""
        return db.query(PDF).filter(PDF.filename == filename, PDF.user_id == user_id).first()