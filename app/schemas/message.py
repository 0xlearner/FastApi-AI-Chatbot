from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List, Any


class MessageBase(BaseModel):
    content: str
    role: str


class MessageCreate(MessageBase):
    file_id: str
    user_id: int


class Message(MessageBase):
    id: int
    file_id: str
    user_id: int
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True
