from abc import ABC,abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.memory.config import MemoryConfig


class MemoryItem(BaseModel):
    id: str # 唯一标识一个记忆
    content: str # 内容
    memory_type: str # 记忆类型
    importance: float # 重要性
    timestamp: datetime # 时间戳
    metadata: dict # 元数据


class Episode(BaseModel):
    episode_id: str # 唯一标识一个情景记忆
    session_id: str # 唯一标识一个会话
    timestamp: datetime # 时间戳
    content: str # 内容
    context: dict # 上下文


class BaseStore(ABC):
    """存储器基类"""
    def __init__(self, config:dict):
        self.config = config

    @abstractmethod
    def add(self,memory_item: MemoryItem,**kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(self) -> List[MemoryItem]:
        raise NotImplementedError

    def get(self,memory_id: str) -> Optional[MemoryItem]:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self,memory_item: MemoryItem,**kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove(self,memory_id: str) -> None:
        raise NotImplementedError

class BaseMemory(ABC):
    """记忆基类

    定义所有记忆类型的通用接口和行为
    """

    def __init__(self, config: MemoryConfig, storage_backend: BaseStore):
        self.config = config
        self.storage = storage_backend
        self.memory_type = self.__class__.__name__.lower().replace("memory", "")

    @abstractmethod
    def add(self, memory_item: MemoryItem) -> str:
        """添加记忆项

        Args:
            memory_item: 记忆项对象

        Returns:
            记忆ID
        """
        pass

    @abstractmethod
    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索相关记忆

        Args:
            query: 查询内容
            limit: 返回数量限制
            **kwargs: 其他检索参数

        Returns:
            相关记忆列表
        """
        pass

    @abstractmethod
    def update(self, memory_id: str, content: str = None,
               importance: float = None, metadata: Dict[str, Any] = None) -> bool:
        """更新记忆

        Args:
            memory_id: 记忆ID
            content: 新内容
            importance: 新重要性
            metadata: 新元数据

        Returns:
            是否更新成功
        """
        pass

    @abstractmethod
    def remove(self, memory_id: str) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在

        Args:
            memory_id: 记忆ID

        Returns:
            是否存在
        """
        pass

    @abstractmethod
    def clear(self):
        """清空所有记忆"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息

        Returns:
            统计信息字典
        """
        pass

    def __str__(self) -> str:
        stats = self.get_stats()
        return f"{self.__class__.__name__}(count={stats.get('count', 0)})"

    def __repr__(self) -> str:
        return self.__str__()


