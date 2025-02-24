from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.core.security import get_current_user
from app.models.domain.user import User
from app.services.pdf_service import PDFService
from app.api.deps import get_pdf_service
from sqlalchemy.orm import Session
from app.core.database import get_db
from fastapi.templating import Jinja2Templates
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
            context["uploaded_file"] = {"filename": file, "file_id": pdf.file_id}

    return templates.TemplateResponse("pdfs.html", context)
