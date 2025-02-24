from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.core.logging_config import get_logger

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
