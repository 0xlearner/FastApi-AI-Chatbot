from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.services.chat_service import ChatService
from app.api.deps import get_chat_service, get_db
from app.models.domain.user import User
from typing import Dict
from app.schemas.chat import ChatRequest
from app.models.domain.message import Message as MessageModel

from typing import Literal


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
        raise HTTPException(
            status_code=403, detail="You don't have access to this PDF")

    response = await chat_service.get_response(
        query=chat_request.query, file_id=file_id, db=db
    )
    return response


@router.get("/{file_id}/messages")
async def get_messages(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get chat messages for a specific PDF"""
    messages = (
        db.query(MessageModel)
        .filter(
            MessageModel.file_id == file_id,
            MessageModel.user_id == current_user.id
        )
        .order_by(MessageModel.created_at.asc())
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        "components/chat-messages.html",
        {"request": request, "messages": messages}
    )


@router.post("/{file_id}/send")
async def send_message(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    db: Session = Depends(get_db),
):
    """Send a message and get response"""
    form_data = await request.form()
    message_text = form_data.get("message")

    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Save user message
    user_message = MessageModel(
        user_id=current_user.id,
        file_id=file_id,
        role="user",
        content=message_text
    )
    db.add(user_message)
    db.commit()

    # Get chatbot response
    response = await chat_service.get_response(
        query=message_text,
        file_id=file_id,
        db=db
    )

    # Save bot message
    bot_message = MessageModel(
        user_id=current_user.id,
        file_id=file_id,
        role="assistant",
        content=response["response"],
        sources=response.get("sources", "[]")
    )
    db.add(bot_message)
    db.commit()

    # Only return the bot's message
    return request.app.state.templates.TemplateResponse(
        "components/chat-messages.html",
        {"request": request, "messages": [bot_message]}
    )


@router.post("/{file_id}/messages/{message_id}/vote")
async def vote_message(
    file_id: str,
    message_id: int,
    vote_type: Literal["upvote", "downvote"],
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handle upvote/downvote for a message"""
    message = db.query(MessageModel).filter(
        MessageModel.id == message_id,
        MessageModel.file_id == file_id,
        MessageModel.role == "assistant"  # Only allow voting on assistant messages
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Update vote count
    if vote_type == "upvote":
        message.upvotes += 1
    else:
        message.downvotes += 1

    db.commit()

    return {"success": True, "upvotes": message.upvotes, "downvotes": message.downvotes}
