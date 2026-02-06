"""消息模块"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel


MessageRole = Literal["system", "user", "assistant","tool"]


@dataclass
class Message:
    """消息基类"""
    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "role": self.role,
        }
    
    def __str__(self) -> str:
        return f"[{self.role}]: {self.content}"


@dataclass
class HumanMessage(Message):
    """人类消息"""

    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(content=content, role="user", metadata=metadata)


@dataclass
class AIMessage(Message):
    """AI消息"""

    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(content=content, role="assistant", metadata=metadata)


@dataclass
class SystemMessage(Message):
    """系统消息"""

    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(content=content, role="system", metadata=metadata)


@dataclass
class ToolMessage(Message):
    """工具消息"""
    tool_name: str = ""
    tool_arguments: str = ""
    tool_call_id: str = ""
    tool_type: str = ""

    def __init__(self, content: str, tool_name: str = "",tool_arguments: str = "", tool_call_id: str = "", tool_type: str = "",
                 metadata: Optional[Dict[str, Any]] = None):
        super().__init__(content=content, role="tool", metadata=metadata)
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments
        self.tool_call_id = tool_call_id
        self.tool_type = tool_type

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = super().to_dict()
        data.update({
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "tool_call_id": self.tool_call_id
        })
        return data
