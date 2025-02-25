from datetime import datetime

from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    sources = Column(JSON, nullable=True)  # For storing source references
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    file_id = Column(String(255), ForeignKey("pdfs.file_id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Use string references for relationships
    user = relationship("User", back_populates="messages")
    votes = relationship("Vote", backref="message",
                         cascade="all, delete-orphan")
