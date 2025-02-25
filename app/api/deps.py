from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.service_container import services
from app.db.session import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Service dependencies with initialization check
def ensure_services_initialized():
    if not services.is_initialized():
        services.initialize_services()
    return services


def get_document_processor():
    return ensure_services_initialized().document_processor


def get_embeddings():
    return ensure_services_initialized().embeddings


def get_vector_store():
    return ensure_services_initialized().vector_store


def get_llm():
    return ensure_services_initialized().llm


def get_websocket_manager():
    return ensure_services_initialized().websocket_manager


def get_pdf_service():
    pdf_service = ensure_services_initialized().pdf_service
    if pdf_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF service not initialized"
        )
    return pdf_service


def get_chat_service():
    return ensure_services_initialized().chat_service
