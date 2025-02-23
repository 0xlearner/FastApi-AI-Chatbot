from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.crud.user import get_user_by_email
from app.services.pdf_service import PDFService
from app.services.chat_service import ChatService
from app.services.rag_pipeline.document_processor import DocumentProcessor
from app.services.rag_pipeline.embeddings import OllamaEmbeddings
from app.services.rag_pipeline.vector_store import PineconeStore
from app.services.rag_pipeline.llm import OllamaLLM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    return user


# Service dependencies
def get_document_processor():
    return DocumentProcessor(
        upload_dir=settings.UPLOAD_DIR,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        batch_size=settings.BATCH_SIZE,
    )


def get_embeddings():
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model_name=settings.EMBEDDING_MODEL_NAME,
    )


def get_vector_store():
    return PineconeStore(
        api_key=settings.PINECONE_API_KEY,
        environment=settings.PINECONE_ENVIRONMENT,
        index_name=settings.PINECONE_INDEX_NAME,
    )


def get_llm():
    return OllamaLLM(
        base_url=settings.OLLAMA_BASE_URL, model_name=settings.LLM_MODEL_NAME
    )


def get_pdf_service(
    document_processor: DocumentProcessor = Depends(get_document_processor),
    embeddings: OllamaEmbeddings = Depends(get_embeddings),
    vector_store: PineconeStore = Depends(get_vector_store),
) -> PDFService:
    return PDFService(
        document_processor=document_processor,
        embeddings=embeddings,
        vector_store=vector_store,
        upload_dir=settings.UPLOAD_DIR,
    )


def get_chat_service(
    embeddings: OllamaEmbeddings = Depends(get_embeddings),
    vector_store: PineconeStore = Depends(get_vector_store),
    llm: OllamaLLM = Depends(get_llm),
    pdf_service: PDFService = Depends(get_pdf_service),
) -> ChatService:
    return ChatService(
        embeddings=embeddings,
        vector_store=vector_store,
        llm=llm,
        pdf_service=pdf_service,
    )
