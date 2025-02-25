from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.core.security import get_current_user
from app.models.domain.user import User
from app.services.pdf_service import PDFService
from app.api.deps import get_pdf_service
from sqlalchemy.orm import Session
from app.core.database import get_db
from fastapi.templating import Jinja2Templates
from app.models.domain.pdf import PDF as PDFModel
from app.models.domain.message import Message as MessageModel
import os

router = APIRouter()

# Get the base directory path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get("/pdfs")
async def pdfs_page(
    request: Request,
    file: str = None,
    current_user: User = Depends(get_current_user),
    pdf_service: PDFService = Depends(get_pdf_service),
    db: Session = Depends(get_db),
):
    context = {
        "request": request,
        "user": current_user,
    }

    if file:
        pdf = pdf_service.get_pdf_by_filename(file, current_user.id, db)
        if pdf:
            context["uploaded_file"] = {
                "filename": file, "file_id": pdf.file_id}

    return templates.TemplateResponse("pdfs.html", context)


@router.get("/chat/{file_id}")
async def chat_page(
    request: Request,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render chat page with PDF viewer"""
    # Verify PDF exists and user has access
    pdf = db.query(PDFModel).filter(
        PDFModel.file_id == file_id,
        PDFModel.user_id == current_user.id
    ).first()

    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")

    # Get existing messages
    messages = (
        db.query(MessageModel)
        .filter(
            MessageModel.file_id == file_id,
            MessageModel.user_id == current_user.id
        )
        .order_by(MessageModel.created_at.asc())
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "pdf": pdf,
            "messages": messages,
            "user": current_user
        }
    )
