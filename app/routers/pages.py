from fastapi import APIRouter, Depends, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from app.core.security import get_current_user, get_current_user_or_none
from app.core.config import settings
from app.models.domain.user import User
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.domain.pdf import PDF as PDFModel
from app.models.domain.message import Message as MessageModel
from app.repositories.pdf_repository import PDFRepository
from typing import Optional

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    return request.app.state.templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": current_user,
            "current_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
    )


@router.get("/pdfs")
async def pdfs_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        pdf_repository = PDFRepository()
        user_pdfs = await pdf_repository.get_user_pdfs(current_user.id, db)
        return request.app.state.templates.TemplateResponse(
            "pdfs.html",
            {
                "request": request,
                "user": current_user,
                "pdfs": user_pdfs,
                "current_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
    except HTTPException as e:
        # If authentication fails, redirect to login
        return RedirectResponse(url="/login", status_code=302)


@router.get("/login")
async def login_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    # If user is already logged in, redirect to PDFs page
    if current_user:
        return RedirectResponse(url="/pdfs", status_code=302)

    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request, "user": None}
    )


@router.get("/signup")
async def signup_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    # If user is already logged in, redirect to PDFs page
    if current_user:
        return RedirectResponse(url="/pdfs", status_code=302)

    return request.app.state.templates.TemplateResponse(
        "signup.html",
        {"request": request, "user": None}
    )


@router.get("/logout")
async def logout_page(request: Request, response: Response):
    """Handle logout and redirect to login page"""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite='lax'
    )
    return RedirectResponse(
        url="/login?message=Successfully logged out",
        status_code=302
    )


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
