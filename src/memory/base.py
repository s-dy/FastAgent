from abc import ABC,abstractmethod
from pydantic import BaseModel
from datetime import datetime

from src.memory.config import MemoryConfig


class MemoryItem(BaseModel):
    id: str # 唯一标识一个记忆
    content: str # 内容
    importance: float # 重要性
    timestamp: datetime # 时间戳
    metadata: dict # 元数据


class Episode(BaseModel):
    episode_id: str # 唯一标识一个情景记忆
    session_id: str # 唯一标识一个会话
    timestamp: datetime # 时间戳
    content: str # 内容
    context: dict # 上下文


class BaseMemory(ABC):
    def __init__(self, config: MemoryConfig, **kwargs) -> None:
        pass

    @abstractmethod
    def add(self, user_id: str, item: MemoryItem) -> str:
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, user_id: str, query: str, limit: int = 5, **kwargs) -> list[MemoryItem]:
        raise NotImplementedError

class BaseStore(ABC):
    """存储器基类"""
    def __init__(self, config:dict):
        self.config = config

    @abstractmethod
    def add(self,**kwargs) -> None:
        raise NotImplementedError
