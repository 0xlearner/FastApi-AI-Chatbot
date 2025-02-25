from fastapi import APIRouter, Request, Response, Depends
from fastapi.templating import Jinja2Templates
from app.core.logging_config import get_logger
from app.core.config import settings
from app.models.domain.user import User
from app.core.security import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = get_logger("auth_routes")


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(
        "signup.html",
        {"request": request}
    )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """Logout user by clearing the cookie"""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite='lax'
    )
    return {"detail": "Successfully logged out"}
