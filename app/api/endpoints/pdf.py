from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException, Request, BackgroundTasks, WebSocket
from sqlalchemy.orm import Session
from app.services.pdf_service import PDFService
from app.core.security import get_current_user
from app.models.domain.user import User
from app.core.database import get_db
from app.core.logging_config import get_logger
from typing import List
import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Dict
import aiofiles
import os
from app.core.config import settings

from app.api.deps import get_pdf_service
from app.core.websocket_manager import ConnectionManager

logger = get_logger('auth_endpoint')

router = APIRouter()

ws_manager = ConnectionManager()

class PDFResponse(BaseModel):
    file_id: str
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True



async def save_upload_file(upload_file: UploadFile, user_id: int, file_id: str) -> tuple[str, bytes]:
    """Save uploaded file and return file path and content"""
    # Create user directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{file_id}_{upload_file.filename}")
    
    # Read file content
    content = await upload_file.read()
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as out_file:
        await out_file.write(content)
    
    return file_path, content

@router.websocket("/progress/{file_id}")
async def websocket_progress(
    websocket: WebSocket,
    file_id: str,
    db: Session = Depends(get_db)
):
    logger.info(f"[{datetime.utcnow()}] New WebSocket connection request for file_id: {file_id}")
    await ws_manager.connect(websocket, file_id)
    try:
        logger.info(f"[{datetime.utcnow()}] WebSocket connection established for file_id: {file_id}")
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
    except Exception as e:
        logger.error(f"WebSocket error for file_id {file_id}: {str(e)}")
    finally:
        await ws_manager.disconnect(websocket, file_id)
        logger.info(f"[{datetime.utcnow()}] WebSocket connection closed for file_id: {file_id}")

@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pdf_service = Depends(get_pdf_service)
) -> Dict:
    logger.info(f"[{datetime.utcnow()}] PDF upload request from user: {current_user.email}")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    try:
        file_id = str(uuid.uuid4())
        logger.info(f"[{datetime.utcnow()}] Generated file_id: {file_id} for file: {file.filename}")
        
        # Save file and get content
        file_path, content = await save_upload_file(file, current_user.id, file_id)
        logger.info(f"[{datetime.utcnow()}] File saved at: {file_path}")
        
        # Add the background task
        background_tasks.add_task(
            pdf_service.process_saved_pdf,
            file_id=file_id,
            file_path=file_path,
            filename=file.filename,
            content=content,
            user_id=current_user.id,
            db=db
        )

        logger.info(f"[{datetime.utcnow()}] Added background task for file_id: {file_id}")
        return {
            "message": "PDF upload started",
            "file_id": file_id
        }
    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/list", response_model=List[PDFResponse])
async def list_pdfs(
    request: Request,
    current_user = Depends(get_current_user),
    pdf_service: PDFService = Depends(get_pdf_service),
    db: Session = Depends(get_db),
):
    try:
        pdfs = await pdf_service.get_user_pdfs(user_id=current_user.id, db=db)
        return pdfs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))