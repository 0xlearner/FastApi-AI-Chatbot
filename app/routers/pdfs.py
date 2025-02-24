from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from app.core.security import get_current_user
from app.models.domain.user import User
from app.core.logging_config import get_logger

logger = get_logger("pdf_routes")
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/pdfs")
async def pdfs_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Get token from cookie
    token = request.cookies.get("access_token")
    logger.info(f"Rendering PDFs page for user: {current_user.email}")
    logger.debug(f"Token available: {'yes' if token else 'no'}")

    if not token:
        logger.error("No access token found in cookie")
        raise HTTPException(status_code=401, detail="Authentication required")

    return templates.TemplateResponse(
        "pdfs.html",
        {
            "request": request,
            "access_token": token,
            "user": current_user
        }
    )
