from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.core.security import get_current_user
from app.models.domain.user import User
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

@router.get("/pdfs", response_class=HTMLResponse)
async def pdfs_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    return templates.TemplateResponse(
        "pdfs.html",
        {
            "request": request,
            "user": current_user
        }
    )