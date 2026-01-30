"""消息模块"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel


MessageRole = Literal["system", "user", "assistant","tool"]

class Message(BaseModel):
    """消息类"""
    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str,Any]] = None

    def __init__(self, content: str, role: MessageRole, **kwargs) -> None:
        super().__init__(
            content=content,
            role=role,
            timestamp=kwargs.get("timestamp", datetime.now()),
            metadata=kwargs.get("metadata", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "role": self.role,
        }
    
    def __str__(self) -> str:
        return f"[{self.role}]: {self.content}"
