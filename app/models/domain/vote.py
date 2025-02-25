from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from app.core.database import Base


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message_id = Column(Integer, ForeignKey("messages.id"))
    vote_type = Column(String(10))  # "upvote" or "downvote"

    # Ensure one vote per user per message
    __table_args__ = (
        UniqueConstraint('user_id', 'message_id',
                         name='uix_user_message_vote'),
    )
