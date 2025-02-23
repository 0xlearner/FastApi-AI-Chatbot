from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.database import get_db
from app.models.domain.user import User as UserModel
from app.schemas.user import UserCreate
from app.core.config import settings


router = APIRouter(tags=["auth"])


@router.post(f"{settings.API_V1_STR}/signup")
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        existing_user = (
            db.query(UserModel).filter(UserModel.email == user_data.email).first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(user_data.password)
        new_user = UserModel(email=user_data.email, hashed_password=hashed_password)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        access_token = create_access_token(
            data={"sub": new_user.email}, expires_delta=timedelta(days=7)
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"email": new_user.email, "id": new_user.id},
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(f"{settings.API_V1_STR}/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=timedelta(days=7)
    )

    response = RedirectResponse(url="/pdfs", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=7 * 24 * 60 * 60,
        samesite="lax",
    )

    return response


@router.post(f"{settings.API_V1_STR}/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"msg": "Logged out successfully"}
