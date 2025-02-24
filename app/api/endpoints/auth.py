from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from app.core import security
from app.core.logging_config import get_logger
from app.core.database import get_db
from app.models.domain.user import User as UserModel
from app.schemas.user import UserCreate, UserResponse, Token

logger = get_logger("auth_endpoint")
router = APIRouter()


@router.get("/check-auth")
async def check_auth(
    request: Request,
    current_user: UserModel = Depends(security.get_current_user)
):
    return {
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email
        }
    }


@router.get("/ws-token")
async def get_ws_token(current_user: UserModel = Depends(security.get_current_user)):
    """Generate a short-lived token for WebSocket authentication"""
    try:
        # Create a short-lived token (e.g., 5 minutes)
        ws_token = security.create_access_token(
            data={"sub": current_user.email},
            expires_delta=timedelta(minutes=5)
        )
        return {"token": ws_token}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate WebSocket token: {str(e)}"
        )


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        logger.debug(f"Login attempt for user: {form_data.username}")

        # Find user
        user = db.query(UserModel).filter(
            UserModel.email == form_data.username).first()
        if not user:
            logger.warning(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Verify password
        if not security.verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Create access token
        access_token = security.create_access_token(
            data={"sub": user.email}, expires_delta=timedelta(days=7)
        )
        logger.info(f"Created access token for user {user.email}")

        # Create response
        response = RedirectResponse(url="/pdfs", status_code=303)

        # Set cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,  # 7 days
            samesite="lax",
            secure=False,  # Set to True in production with HTTPS
            path="/",
        )

        return response

    except HTTPException as e:
        logger.error(f"Login failed: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("/signup")
async def signup(
    response: Response,
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        logger.debug(f"Signup attempt for email: {user_data.email}")

        # Check existing user
        existing_user = (
            db.query(UserModel).filter(
                UserModel.email == user_data.email).first()
        )
        if existing_user:
            logger.warning(f"Email already registered: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user
        hashed_password = security.get_password_hash(user_data.password)
        new_user = UserModel(
            email=user_data.email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow(),
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"Created new user: {new_user.email} (ID: {new_user.id})")

        # Create access token
        access_token = security.create_access_token(
            data={"sub": new_user.email}, expires_delta=timedelta(days=7)
        )

        # Set cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,
            samesite="lax",
            secure=False,  # Set to True in production with HTTPS
            path="/",
        )

        return Token(access_token=access_token, token_type="bearer")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserModel = Depends(security.get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email)


@router.get("/debug/users")
async def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to list all users - REMOVE IN PRODUCTION"""
    users = db.query(UserModel).all()
    return [{"id": user.id, "email": user.email} for user in users]
