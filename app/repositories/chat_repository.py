from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.domain.message import Message


class ChatRepository:
    def get_chat_history(
        self,
        db: Session,
        file_id: str,
        user_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        query = db.query(Message).filter(
            Message.file_id == file_id,
            Message.user_id == user_id
        ).order_by(Message.created_at.asc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def save_message(
        self,
        db: Session,
        user_id: int,
        file_id: str,
        content: str,
        role: str,
        sources: dict = None
    ) -> Message:
        message = Message(
            user_id=user_id,
            file_id=file_id,
            content=content,
            role=role,
            sources=sources
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def delete_chat_history(
        self,
        db: Session,
        file_id: str,
        user_id: int
    ) -> bool:
        db.query(Message).filter(
            Message.file_id == file_id,
            Message.user_id == user_id
        ).delete()
        db.commit()
        return True
