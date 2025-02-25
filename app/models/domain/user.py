from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Use string references for relationships to avoid circular imports
    pdfs = relationship("PDF", back_populates="user")
    messages = relationship("Message", back_populates="user")

    def __str__(self):
        return f"Current User's Login: {self.email}"
