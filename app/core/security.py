from functools import lru_cache
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import logging
from app.core.config import settings
from app.core.database import get_db
from app.crud.user import get_user_by_email
from app.models.domain.user import User
from app.schemas.user import TokenData

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Get token from cookie
        token = request.cookies.get("access_token")
        logger.debug(
            f"Token from cookie: {
                     token[:10]}..."
            if token
            else "No token"
        )

        if not token:
            # Try authorization header as fallback
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                logger.debug(f"Token from header: {token[:10]}...")

        if not token:
            logger.error("No token found in request")
            raise credentials_exception

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("sub")
            if email is None:
                logger.error("No email in token payload")
                raise credentials_exception
        except JWTError as e:
            logger.error(f"JWT decode error: {str(e)}")
            raise credentials_exception

        user = get_user_by_email(db, email=email)
        if user is None:
            logger.error(f"User not found: {email}")
            raise credentials_exception

        return user

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception


def extract_token_from_request(request: Request) -> Optional[str]:
    logger.debug(f"Headers: {request.headers}")
    logger.debug(f"Cookies: {request.cookies}")

    # Try getting token from Authorization header
    auth_header = request.headers.get("Authorization")
    logger.debug(f"Auth header: {auth_header}")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Try getting token from cookie
    cookie_token = request.cookies.get("access_token")
    logger.debug(f"Cookie token: {cookie_token}")
    if cookie_token:
        return cookie_token

    return None


@lru_cache(maxsize=1024)
def get_cached_user_validation(token: str) -> TokenData:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return TokenData(username=username)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    Returns the token payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            logger.error("No email in token payload")
            return None
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Token decode error: {str(e)}")
        return None
