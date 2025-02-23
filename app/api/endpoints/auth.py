from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime

from app.core import security
from app.core.logging_config import get_logger
from app.core.database import get_db
from app.models.domain.user import User as UserModel
from app.schemas.user import UserCreate, UserResponse, Token

logger = get_logger('auth_endpoint')
router = APIRouter()

@router.post("/signup", response_model=Token)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        logger.debug(f"Signup attempt for email: {user_data.email}")
        
        # Check existing users
        existing_user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
        if existing_user:
            logger.warning(f"Email already registered: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        hashed_password = security.get_password_hash(user_data.password)
        new_user = UserModel(
            email=user_data.email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow()
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.debug(f"Created new user: {new_user.email} (ID: {new_user.id})")

        # Create access token
        access_token = security.create_access_token(
            data={"sub": new_user.email},
            expires_delta=timedelta(days=7)
        )

        return Token(
            access_token=access_token,
            token_type="bearer"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        logger.debug(f"Login attempt for user: {form_data.username}")
        
        user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
        if not user:
            logger.warning(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if not security.verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Create access token
        access_token = security.create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=7)
        )
        logger.debug(f"Created access token for user {user.email}")

        token_response = {
            "access_token": access_token,
            "token_type": "bearer"
        }

        # Check if request wants JSON response
        accept_header = request.headers.get("accept", "").lower()
        wants_json = "application/json" in accept_header

        if wants_json:
            logger.debug("Returning JSON response")
            return JSONResponse(content=token_response)
        else:
            logger.debug("Returning redirect response with cookie")
            response = RedirectResponse(url="/pdfs", status_code=303)
            # Set the cookie without Bearer prefix
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=False,
                max_age=7 * 24 * 60 * 60,
                samesite="lax",
                secure=False,
                path="/"  # Added path
            )
            # Also set the token in response headers
            response.headers["Authorization"] = f"Bearer {access_token}"
            return response

    except HTTPException as e:
        logger.error(f"Login error: {str(e)}")
        if "application/json" in request.headers.get("accept", "").lower():
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        raise e

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: UserModel = Depends(security.get_current_user)
):
    return UserResponse(
        id=current_user.id,
        email=current_user.email
    )

@router.get("/debug/users")
async def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to list all users - REMOVE IN PRODUCTION"""
    users = db.query(UserModel).all()
    return [{"id": user.id, "email": user.email} for user in users]