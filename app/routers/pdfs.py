from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
import aiofiles

from app.core.database import get_db
from app.core.security import get_current_user
from app.api.deps import get_pdf_service
from app.models.domain.user import User
from app.models.domain.pdf import PDF as PDFModel
from app.schemas.pdf import PDF as PDFSchema
from app.services.pdf_service import PDFService
from app.core.config import settings

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])


@router.get("/", response_model=List[PDFSchema])
async def get_pdfs(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[PDFSchema]:
    pdfs = db.query(PDFModel).filter(PDFModel.user_id == current_user.id).all()
    return pdfs


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pdf_service: PDFService = Depends(get_pdf_service),
) -> JSONResponse:
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Save file
        file_id = str(uuid.uuid4())
        user_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{file_id}_{file.filename}")

        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)

        # Create PDF record
        pdf_db = PDFModel(
            file_id=file_id,
            filename=file.filename,
            file_path=file_path,
            user_id=current_user.id,
            is_processed=False
        )
        db.add(pdf_db)
        db.commit()

        # Start processing in background task
        background_tasks = BackgroundTasks()
        background_tasks.add_task(pdf_service.save_and_process_pdf, pdf_db, db)

        return JSONResponse({
            "status": "success",
            "message": "PDF uploaded successfully",
            "file_id": file_id
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_id}/status")
async def get_processing_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    pdf = db.query(PDFModel).filter(
        PDFModel.file_id == file_id,
        PDFModel.user_id == current_user.id
    ).first()

    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")

    return JSONResponse({
        "is_processed": pdf.is_processed
    })


@router.get("/view/{file_id}", response_class=FileResponse)
async def view_pdf(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    pdf = (
        db.query(PDFModel)
        .filter(PDFModel.file_id == file_id, PDFModel.user_id == current_user.id)
        .first()
    )

    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        pdf.file_path, media_type="application/pdf", filename=pdf.filename
    )
