from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.services.pdf_service import PDFService
from app.api.deps import get_current_user, get_db, get_pdf_service
from typing import List
from pydantic import BaseModel
from datetime import datetime


class PDFResponse(BaseModel):
    file_id: str
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True


router = APIRouter()


@router.post("/upload", response_model=PDFResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    pdf_service: PDFService = Depends(get_pdf_service),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        result = await pdf_service.save_and_process_pdf(
            file=file, user_id=current_user.id, db=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[PDFResponse])
async def list_pdfs(
    current_user=Depends(get_current_user),
    pdf_service: PDFService = Depends(get_pdf_service),
    db: Session = Depends(get_db),
):
    try:
        pdfs = await pdf_service.get_user_pdfs(user_id=current_user.id, db=db)
        return pdfs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
