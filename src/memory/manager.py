import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.memory.base import MemoryItem
from src.memory.config import MemoryConfig
from src.memory.memory_types import WorkingMemory,EpisodicMemory,SemanticMemory,PerceptualMemory
from src.memory.store import MemoryStore
from src.monitor import monitor_task_status


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
            self.memory_types['working'] = WorkingMemory(self.config, MemoryStore())

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
            importance: Optional[float] = None,
            metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """添加记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性分数 (0-1)
            metadata: 元数据

        Returns:
            记忆ID
        """
        if not metadata.get('user_id'):
            raise Exception('添加记忆需要指定user_id')
        # 计算重要性
        if importance is None:
            importance = self._calculate_importance(content, metadata)

        # 创建记忆项
        memory_item = MemoryItem(
            id=self._generate_id(),
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now(),
            importance=importance,
            metadata=metadata or {}
        )
        # 添加到对应的记忆类型
        if memory_type in self.memory_types:
            memory_id = self.memory_types[memory_type].add(memory_item)
            monitor_task_status(f"添加记忆到 {memory_type}: {memory_id}")
            return memory_id
        else:
            monitor_task_status(f"不支持的记忆类型: {memory_type}")
            raise ValueError(f"不支持的记忆类型: {memory_type}")

    def retrieve_memories(
            self,
            query: str,
            memory_types: Optional[List[str]] = None,
            limit: int = 10,
            min_importance: float = 0.0,
    ) -> List[MemoryItem]:
        """检索记忆

        Args:
            query: 查询内容
            memory_types: 要检索的记忆类型列表
            limit: 返回数量限制
            min_importance: 最小重要性阈值

        Returns:
            检索到的记忆列表
        """
        if memory_types is None:
            memory_types = list(self.memory_types.keys())

        # 从各个记忆类型中检索
        all_results = []
        per_type_limit = max(1, limit // len(memory_types))

        for memory_type in memory_types:
            if memory_type in self.memory_types:
                memory_instance = self.memory_types[memory_type]
                try:
                    # 使用各个记忆类型自己的检索方法
                    type_results = memory_instance.retrieve(
                        query=query,
                        limit=per_type_limit,
                        min_importance=min_importance,
                        user_id=self.user_id
                    )
                    all_results.extend(type_results)
                except Exception as e:
                    monitor_task_status(f"检索 {memory_type} 记忆时出错: {e}",level='WARNING')
                    continue

        # 按重要性和相关性排序
        all_results.sort(key=lambda x: x.importance, reverse=True)
        return all_results[:limit]

    def update_memory(
            self,
            memory_id: str,
            content: Optional[str] = None,
            importance: Optional[float] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新记忆

        Args:
            memory_id: 记忆ID
            content: 新内容
            importance: 新重要性
            metadata: 新元数据

        Returns:
            是否更新成功
        """
        for memory_type, memory_instance in self.memory_types.items():
            if memory_instance.has_memory(memory_id):
                return memory_instance.update(memory_id, content, importance, metadata)

        monitor_task_status(f"未找到记忆: {memory_id}", level='WARNING')
        return False

    def remove_memory(self, memory_id: str) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否删除成功
        """
        for memory_type, memory_instance in self.memory_types.items():
            if memory_instance.has_memory(memory_id):
                return memory_instance.remove(memory_id)

        monitor_task_status(f"未找到记忆: {memory_id}", level='WARNING')
        return False

    def forget_memories(
            self,
            strategy: str = "importance_based",
            threshold: float = 0.1,
            max_age_days: int = 30
    ) -> int:
        """记忆遗忘机制

        Args:
            strategy: 遗忘策略 ("importance_based", "time_based", "capacity_based")
            threshold: 遗忘阈值
            max_age_days: 最大保存天数

        Returns:
            遗忘的记忆数量
        """
        total_forgotten = 0

        for memory_type, memory_instance in self.memory_types.items():
            if hasattr(memory_instance, 'forget'):
                forgotten = memory_instance.forget(strategy, threshold, max_age_days)
                total_forgotten += forgotten

        monitor_task_status(f"记忆遗忘完成: {total_forgotten} 条记忆", level='WARNING')
        return total_forgotten

    def consolidate_memories(
            self,
            from_type: str = "working",
            to_type: str = "episodic",
            importance_threshold: float = 0.7
    ) -> int:
        """记忆整合 - 将重要的短期记忆转换为长期记忆

        Args:
            from_type: 源记忆类型
            to_type: 目标记忆类型
            importance_threshold: 重要性阈值

        Returns:
            整合的记忆数量
        """
        if from_type not in self.memory_types or to_type not in self.memory_types:
            monitor_task_status(f"记忆类型不存在: {from_type} -> {to_type}", level='WARNING')
            return 0

        # 获取高重要性的源记忆
        source_memory = self.memory_types[from_type]
        target_memory = self.memory_types[to_type]

        # 获取需要整合的记忆
        all_memories = source_memory.get_all()
        candidates = [
            m for m in all_memories
            if m.importance >= importance_threshold
        ]

        consolidated_count = 0
        for memory in candidates:
            # 移动到目标记忆类型
            if source_memory.remove(memory.id):
                memory.memory_type = to_type
                memory.importance *= 1.1  # 提升重要性
                target_memory.add(memory)
                consolidated_count += 1

        monitor_task_status(f"记忆整合完成: {consolidated_count} 条记忆从 {from_type} 转移到 {to_type}")
        return consolidated_count

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        stats = {
            "user_id": self.user_id,
            "enabled_types": list(self.memory_types.keys()),
            "total_memories": 0,
            "memories_by_type": {},
        }

        for memory_type, memory_instance in self.memory_types.items():
            type_stats = memory_instance.get_stats()
            stats["memories_by_type"][memory_type] = type_stats
            # 使用count字段（活跃记忆数），而不是total_count（包含已遗忘的）
            stats["total_memories"] += type_stats.get("count", 0)

        return stats

    def clear_all_memories(self):
        """清空所有记忆"""
        for memory_type, memory_instance in self.memory_types.items():
            memory_instance.clear()
        monitor_task_status("所有记忆已清空")

    def _calculate_importance(self, content: str, metadata: Optional[Dict[str, Any]]) -> float:
        """计算记忆重要性"""
        importance = 0.5  # 基础重要性

        # 基于内容长度
        if len(content) > 100:
            importance += 0.1

        # 基于关键词
        important_keywords = ["重要", "关键", "必须", "注意", "警告", "错误"]
        if any(keyword in content for keyword in important_keywords):
            importance += 0.2

        # 基于元数据
        if metadata:
            if metadata.get("priority") == "high":
                importance += 0.3
            elif metadata.get("priority") == "low":
                importance -= 0.2

        return max(0.0, min(1.0, importance))

    def _generate_id(self) -> str:
        """生成记忆ID"""
        return str(uuid.uuid4().hex)
