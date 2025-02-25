from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    HTTPException,
    Request,
    File,
    BackgroundTasks,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.domain import User
from app.core.logging_config import get_logger
from typing import List
import os
import aiofiles
from typing import Dict
from datetime import datetime
import uuid
from app.api.deps import get_websocket_manager
from app.core.security import decode_access_token
from app.schemas.pdf import PDF as PDFSchema
from app.models.domain.pdf import PDF as PDFModel
from app.services.pdf_service import PDFService
from app.api.deps import get_pdf_service
from app.core.websocket_manager import WebSocketManager
from app.repositories.pdf_repository import PDFRepository
from app.core.config import settings


logger = get_logger("auth_endpoint")

router = APIRouter()

ws_manager = WebSocketManager()


@router.websocket("/ws/{file_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    file_id: str,
    token: str = None,
    websocket_manager=Depends(get_websocket_manager),
    db: Session = Depends(get_db)
):
    try:
        # Validate token
        if not token:
            logger.warning("WebSocket connection attempt without token")
            await websocket.close(code=4001, reason="No authentication token provided")
            return

        try:
            # Verify the token and get user email
            payload = decode_access_token(token)
            if not payload or "sub" not in payload:
                logger.warning("Invalid token in WebSocket connection attempt")
                await websocket.close(code=4002, reason="Invalid authentication token")
                return

            # Get user from database
            user = db.query(User).filter(User.email == payload["sub"]).first()
            if not user:
                logger.warning(f"User not found for email: {payload['sub']}")
                await websocket.close(code=4003, reason="User not found")
                return

            # Accept the connection
            await websocket.accept()
            logger.info(f"WebSocket connection accepted for user {
                        user.id} and file {file_id}")

            # Connect to WebSocket manager
            await websocket_manager.connect(websocket, file_id, user.id)

            try:
                # Keep the connection alive until client disconnects
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {
                            user.id} and file {file_id}")
                await websocket_manager.disconnect(websocket, file_id, user.id)

        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            await websocket.close(code=4002, reason="Invalid authentication token")
            return

    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            pass


@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pdf_service: PDFService = Depends(get_pdf_service)
) -> Dict:
    logger.info(f"[{datetime.utcnow()}] PDF upload request from user: {
                current_user.email}")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    try:
        file_id = str(uuid.uuid4())
        logger.info(f"[{datetime.utcnow()}] Generated file_id: {
                    file_id} for file: {file.filename}")

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

        logger.info(
            f"[{datetime.utcnow()}] Added background task for file_id: {file_id}")
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


@router.get("/list", response_model=List[PDFSchema])
async def list_pdfs(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        pdf_repository = PDFRepository()
        pdfs = await pdf_repository.get_user_pdfs(user_id=current_user.id, db=db)
        return pdfs
    except Exception as e:
        logger.error(f"Error listing PDFs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/view/{file_id}")
async def view_pdf(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream PDF file for viewing"""
    # Check if PDF exists and user has access
    pdf = db.query(PDFModel).filter(
        PDFModel.file_id == file_id,
        PDFModel.user_id == current_user.id
    ).first()

    if not pdf:
        raise HTTPException(
            status_code=404,
            detail="PDF not found or you don't have access to it"
        )

    # Check if file exists
    if not os.path.exists(pdf.file_path):
        raise HTTPException(
            status_code=404,
            detail="PDF file not found on server"
        )

    # Return the PDF file
    return FileResponse(
        pdf.file_path,
        media_type="application/pdf",
        filename=pdf.filename,
        headers={
            "Content-Disposition": f"inline; filename={pdf.filename}",
            "Cache-Control": "no-cache"
        }
    )


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
