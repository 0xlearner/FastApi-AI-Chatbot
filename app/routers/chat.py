from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict, List
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.api.deps import get_chat_service
from app.models.domain.user import User
from app.models.domain.pdf import PDF as PDFModel
from app.models.domain.message import Message as MessageModel
from app.schemas.message import Message as MessageSchema
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/{file_id}/messages", response_model=None)
async def get_messages(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    # Get chat history
    messages = (
        db.query(MessageModel)
        .filter(
            MessageModel.file_id == file_id, MessageModel.user_id == current_user.id
        )
        .order_by(MessageModel.created_at.asc())
        .all()
    )

    # Get templates from app state
    templates = request.app.state.templates

    # Render messages template
    return templates.TemplateResponse(
        "components/chat-messages.html", {
            "request": request, "messages": messages}
    )


@router.post("/{file_id}/send", response_model=None)
async def send_message(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> HTMLResponse:
    form_data = await request.form()
    message_text = form_data.get("message")

    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Save user message
    user_message = MessageModel(
        user_id=current_user.id, file_id=file_id, role="user", content=message_text
    )
    db.add(user_message)
    db.commit()

    # Get chatbot response
    response = await chat_service.get_response(message_text, file_id, db)

    # Save bot message
    bot_message = MessageModel(
        user_id=current_user.id,
        file_id=file_id,
        role="assistant",
        content=response["response"],
        sources=json.dumps(response["sources"]),
    )
    db.add(bot_message)
    db.commit()

    # Get templates from app state
    templates = request.app.state.templates

    # Return both messages using the template
    return templates.TemplateResponse(
        "components/chat-messages.html",
        {"request": request, "messages": [user_message, bot_message]},
    )
