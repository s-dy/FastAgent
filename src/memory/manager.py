import uuid
from datetime import datetime
from typing import Optional

from src.memory.base import MemoryItem
from src.memory.config import MemoryConfig
from src.memory.memory_types import WorkingMemory,EpisodicMemory,SemanticMemory,PerceptualMemory


class MemoryManager:
    """记忆管理器 - 统一的记忆操作接口"""
    def __init__(
        self,
        user_id: str,
        config: Optional[MemoryConfig],
    ):
        self.user_id = user_id
        self.config = config

        # 初始化各类型记忆
        self.memory_types = {}

        if self.config.enable_working:
            self.memory_types['working'] = WorkingMemory(self.config)

        if self.config.enable_episodic:
            self.memory_types['episodic'] = EpisodicMemory(self.config)

        if self.config.enable_semantic:
            self.memory_types['semantic'] = SemanticMemory(self.config)

        if self.config.enable_perceptual:
            self.memory_types['perceptual'] = PerceptualMemory(self.config)

    def add_memory(
        self,
        content: str,
        memory_type: str = "working",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        添加记忆
        :param content: 记忆内容
        :param memory_type: 记忆类型
        :param importance: 记忆重要性
        :param metadata: 记忆元数据
        """
        memory_id = uuid.uuid4().hex
        memory_item = MemoryItem(id=memory_id,content=content,importance=importance,metadata=metadata,timestamp=datetime.now())
        if hasattr(self.memory_types.get(memory_type),'add'):
            self.memory_types[memory_type].add(self.user_id, memory_item)
            return memory_id
        raise ValueError

    def retrieve_memories(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] = None,
        min_importance: float = 0.1,
    ) -> list[MemoryItem]:
        """
        检索记忆
        :param query: 查询内容
        :param limit: 检索限制
        :param memory_types: 记忆类型
        :param min_importance: 最小重要性
        :return: 检索结果
        """
        result = []
        if memory_types is None:
            memory_types = []
        for memory_type in memory_types:
            if hasattr(self.memory_types.get(memory_type), 'retrieve'):
                retrieve_result = self.memory_types[memory_type].retrieve(self.user_id, query, limit)
                result.extend(retrieve_result)

        result = list(filter(lambda i: i.importance >= min_importance, result))
        return result
        

    def forget_memories(
        self,
        strategy: str = "importance_based",
        threshold: float = 0.1,
        max_age_days: int = 30
    ):
        """
        遗忘记忆
        :param strategy: 遗忘策略
        :param threshold: 遗忘阈值
        :param max_age_days: 最大年龄天数
        """

    def consolidate_memories(
        self,
        from_type: str = "working",
        to_type: str = "episodic",
        importance_threshold: float = 0.7
    ):
        """
        整合记忆
        :param from_type: 源记忆类型
        :param to_type: 目标记忆类型
        :param importance_threshold: 重要性阈值
        """
    
    def get_summary(self, memory_types: list[str] = None) -> str:
        """
        获取记忆摘要
        :param memory_types: 记忆类型
        :return: 记忆摘要
        """

    def update_memory(self, memory_id: str, content: str = None, importance: float = None, metadata: dict = None) -> str:
        """
        更新记忆
        :param memory_id: 记忆ID
        :param content: 记忆内容
        :param importance: 记忆重要性
        :param metadata: 记忆元数据
        """

    def remove_memory(self, memory_id: str) -> str:
        """
        删除记忆
        :param memory_id: 记忆ID
        """

    def clear_all_memories(self) -> str:
        """
        删除所有记忆
        """
