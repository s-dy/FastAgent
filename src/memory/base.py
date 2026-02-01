import json
from abc import ABC,abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.memory.config import MemoryConfig


class MemoryItem(BaseModel):
    """记忆项"""
    id: str # 唯一标识一个记忆
    content: str # 内容
    memory_type: str # 记忆类型
    importance: float # 重要性
    timestamp: datetime # 时间戳
    metadata: dict # 元数据


class Episode(BaseModel):
    """情景记忆中的单个情景"""
    episode_id: str # 唯一标识一个情景记忆
    user_id: str # 用户ID
    session_id: str # 唯一标识一个会话
    timestamp: datetime # 时间戳
    content: str # 内容
    context: dict # 上下文
    outcome: dict # 结果
    importance: float # 重要性


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


class BaseDocumentStore(ABC):
    """文档存储基类"""
    _instances = {}  # 存储已创建的实例
    _initialized_dbs = set()  # 存储已初始化的数据库配置

    def __new__(cls, config: Dict[str, Any]):
        """单例模式，同一配置只创建一个实例"""
        config_key = json.dumps(config, sort_keys=True)
        if config_key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[config_key] = instance
        return cls._instances[config_key]

    def __init__(self, config: Dict[str, Any]):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return
        # 初始化数据库（只初始化一次）
        config_key = json.dumps(config, sort_keys=True)
        if config_key not in self._initialized_dbs:
            self._init_database()
            self._initialized_dbs.add(config_key)

        self._initialized = True

    @abstractmethod
    def _init_database(self):
        raise NotImplementedError

    @abstractmethod
    def add_memory(
            self,
            memory_id: str,
            user_id: str,
            content: str,
            memory_type: str,
            timestamp: int,
            importance: float,
            properties: Dict[str, Any] = None
    ) -> str:
        """添加记忆"""
        pass

    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取单个记忆"""
        pass

    @abstractmethod
    def search_memories(
            self,
            user_id: Optional[str] = None,
            memory_type: Optional[str] = None,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None,
            importance_threshold: Optional[float] = None,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索记忆"""
        pass

    @abstractmethod
    def update_memory(
            self,
            memory_id: str,
            content: str = None,
            importance: float = None,
            properties: Dict[str, Any] = None
    ) -> bool:
        """更新记忆"""
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

    @abstractmethod
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        pass

    @abstractmethod
    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加文档"""
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档"""
        pass


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


