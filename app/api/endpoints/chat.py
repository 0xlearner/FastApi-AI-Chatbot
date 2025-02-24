from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.services.chat_service import ChatService
from app.api.deps import get_chat_service
from app.core.database import get_db
from typing import Dict
from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str


router = APIRouter()


@router.post("/chat/{file_id}", response_model=Dict)
async def chat(
    file_id: str,
    chat_request: ChatRequest,
    current_user=Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    db: Session = Depends(get_db),
):
    # Verify if the user has access to this PDF
    if not await chat_service.verify_pdf_access(file_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="You don't have access to this PDF")

    response = await chat_service.get_response(
        query=chat_request.query, file_id=file_id, db=db
    )
    return response
