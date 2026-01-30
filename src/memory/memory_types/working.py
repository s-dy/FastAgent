from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.memory.config import MemoryConfig
from src.memory.base import MemoryItem, BaseMemory
from utils.calculate import calculate_keyword_relevance, calculate_time_recency


class WorkingMemory(BaseMemory):
    """工作记忆实现
    特点：
    - 容量有限（默认50条）+ TTL自动清理
    - 纯内存存储，访问速度极快
    - 混合检索：TF-IDF向量化 + 关键词匹配

    工作记忆是记忆系统中最活跃的部分，它负责存储当前对话会话中的临时信息。工作记忆的设计重点在于快速访问和自动清理，这种设计确保了系统的响应速度和资源效率。

    工作记忆采用了纯内存存储方案，配合TTL（Time To Live）机制进行自动清理。这种设计的优势在于访问速度极快，但也意味着工作记忆的内容在系统重启后会丢失。这种特性正好符合工作记忆的定位，存储临时的、易变的信息。
    """
    def __init__(self, config: MemoryConfig, storage_backend):
        super().__init__(config, storage_backend)

        # 工作记忆特定配置
        self.max_capacity = self.config.working_memory_capacity
        self.max_tokens = self.config.working_memory_tokens
        # 纯内存TTL（分钟），可通过在 MemoryConfig 上挂载 working_memory_ttl_minutes 覆盖
        self.max_age_minutes = getattr(self.config, 'working_memory_ttl_minutes', 120)
        self.current_tokens = 0
        self.session_start = datetime.now()


    def add(self, memory_item: MemoryItem) -> str:
        """添加工作记忆"""
        # 过期清理
        self._expire_old_memories()
        # 计算优先级（重要性 + 时间衰减）
        priority = self._calculate_priority(memory_item)

        self.storage.add(memory_item,priority=priority)

        # 更新token计数
        self.current_tokens += len(memory_item.content.split())

        # 检查容量限制
        self._enforce_capacity_limits()
        return memory_item.id

    def retrieve(self, query: str, limit: int = 5, user_id: str = None, **kwargs) -> List[MemoryItem]:
        """检索工作记忆 - 混合语义向量检索和关键词匹配"""
        # 过期清理
        self._expire_old_memories()
        memories = self.get_all()
        if not memories:
            return []
        # 过滤已遗忘的记忆
        active_memories = [m for m in memories if not m.metadata.get("forgotten", False)]
        # 按用户ID过滤（如果提供）
        filtered_memories = active_memories
        if user_id:
            filtered_memories = [m for m in active_memories if m.metadata.get('user_id') == user_id]
        if not filtered_memories:
            return []
        # 尝试语义向量检索（如果有嵌入模型）
        vector_scores = {}
        try:
            # 简单的语义相似度计算（使用TF-IDF或其他轻量级方法）
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            # 准备文档
            documents = [query] + [m.content for m in filtered_memories]

            # TF-IDF向量化
            vectorizer = TfidfVectorizer(stop_words=None, lowercase=True)
            tfidf_matrix = vectorizer.fit_transform(documents)

            # 计算相似度
            query_vector = tfidf_matrix[0:1]
            doc_vectors = tfidf_matrix[1:]
            similarities = cosine_similarity(query_vector, doc_vectors).flatten()

            # 存储向量分数
            for i, memory in enumerate(filtered_memories):
                vector_scores[memory.id] = similarities[i]

        except Exception as e:
            # 如果向量检索失败，回退到关键词匹配
            vector_scores = {}

        # 计算最终分数
        scored_memories = []
        for memory in filtered_memories:
            # 获取向量分数（如果有）
            vector_score = vector_scores.get(memory.id, 0.0)

            # 关键词匹配分数
            keyword_score = calculate_keyword_relevance(query,memory.content)
            # 混合分数：向量检索 + 关键词匹配
            if vector_score > 0:
                base_relevance = vector_score * 0.7 + keyword_score * 0.3
            else:
                base_relevance = keyword_score

            # 时间衰减
            time_decay = calculate_time_recency(memory.timestamp)
            base_relevance *= time_decay

            # 重要性权重
            importance_weight = 0.8 + (memory.importance * 0.4)
            final_score = base_relevance * importance_weight
            if final_score > 0:
                scored_memories.append((final_score, memory))

        # 按分数排序并返回
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored_memories[:limit]]

    def update(
            self,
            memory_id: str,
            content: str = None,
            importance: float = None,
            metadata: Dict[str, Any] = None
    ) -> bool:
        """更新工作记忆"""
        memories = self.get_all()
        for memory in memories:
            if memory.id == memory_id:
                old_tokens = len(memory.content.split())

                if content is not None:
                    memory.content = content
                    # 更新token计数
                    new_tokens = len(content.split())
                    self.current_tokens = self.current_tokens - old_tokens + new_tokens

                if importance is not None:
                    memory.importance = importance

                if metadata is not None:
                    memory.metadata.update(metadata)

                priority = self._calculate_priority(memory)
                self.storage.update(memory,priority=priority)

                return True
        return False

    def remove(self, memory_id: str) -> bool:
        """删除工作记忆"""
        memories = self.get_all()
        for i, memory in enumerate(memories):
            if memory.id == memory_id:
                self.storage.remove(memory_id)
                # 更新token计数
                self.current_tokens -= len(memory.content.split())
                self.current_tokens = max(0, self.current_tokens)

                return True
        return False

    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return any(memory.id == memory_id for memory in self.get_all())

    def clear(self):
        """清空所有工作记忆"""
        self.storage.clear()
        self.current_tokens = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取工作记忆统计信息"""
        # 过期清理（惰性）
        self._expire_old_memories()

        # 工作记忆中的记忆都是活跃的（已遗忘的记忆会被直接删除）
        active_memories = self.get_all()

        return {
            "count": len(active_memories),  # 活跃记忆数量
            "forgotten_count": 0,  # 工作记忆中已遗忘的记忆会被直接删除
            "current_tokens": self.current_tokens,
            "max_capacity": self.max_capacity,
            "max_tokens": self.max_tokens,
            "max_age_minutes": self.max_age_minutes,
            "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            "avg_importance": sum(m.importance for m in active_memories) / len(
                active_memories) if active_memories else 0.0,
            "capacity_usage": len(active_memories) / self.max_capacity if self.max_capacity > 0 else 0.0,
            "token_usage": self.current_tokens / self.max_tokens if self.max_tokens > 0 else 0.0,
            "memory_type": "working"
        }

    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """获取最近的记忆"""
        sorted_memories = sorted(
            self.get_all(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        return sorted_memories[:limit]

    def get_important(self, limit: int = 10) -> List[MemoryItem]:
        """获取重要记忆"""
        sorted_memories = sorted(
            self.get_all(),
            key=lambda x: x.importance,
            reverse=True
        )
        return sorted_memories[:limit]

    def get_all(self) -> List[MemoryItem]:
        """获取所有记忆"""
        return self.storage.list()

    def forget(self, strategy: str = "importance_based", threshold: float = 0.1, max_age_days: int = 1) -> int:
        """工作记忆遗忘机制"""
        forgotten_count = 0
        current_time = datetime.now()

        memories = self.get_all()
        to_remove = []

        # 始终先执行TTL过期（分钟级）
        cutoff_ttl = current_time - timedelta(minutes=self.max_age_minutes)
        for memory in memories:
            if memory.timestamp < cutoff_ttl:
                to_remove.append(memory.id)

        if strategy == "importance_based":
            # 删除低重要性记忆
            for memory in memories:
                if memory.importance < threshold:
                    to_remove.append(memory.id)

        elif strategy == "time_based":
            # 删除过期记忆（工作记忆通常以小时计算）
            cutoff_time = current_time - timedelta(hours=max_age_days * 24)
            for memory in memories:
                if memory.timestamp < cutoff_time:
                    to_remove.append(memory.id)

        elif strategy == "capacity_based":
            # 删除超出容量的记忆
            if len(memories) > self.max_capacity:
                # 按优先级排序，删除最低的
                sorted_memories = sorted(
                    memories,
                    key=lambda m: self._calculate_priority(m)
                )
                excess_count = len(memories) - self.max_capacity
                for memory in sorted_memories[:excess_count]:
                    to_remove.append(memory.id)

        # 执行删除
        for memory_id in to_remove:
            if self.remove(memory_id):
                forgotten_count += 1

        return forgotten_count

    def _calculate_priority(self, memory: MemoryItem) -> float:
        """计算记忆优先级"""
        # 基础优先级 = 重要性
        priority = memory.importance

        # 时间衰减
        time_decay = calculate_time_recency(memory.timestamp)
        priority *= time_decay

        return priority


    def _enforce_capacity_limits(self):
        """强制执行容量限制"""
        memories = self.get_all()
        # 检查记忆数量限制
        while len(memories) > self.max_capacity:
            self._remove_lowest_priority_memory()

        # 检查token限制
        while self.current_tokens > self.max_tokens:
            self._remove_lowest_priority_memory()

    def _expire_old_memories(self):
        """按TTL清理过期记忆，并同步更新堆与token计数"""
        memories = self.get_all()
        if not memories:
            return
        cutoff_time = datetime.now() - timedelta(minutes=self.max_age_minutes)
        # 过滤保留的记忆
        kept: List[MemoryItem] = []
        removed_token_sum = 0
        for m in memories:
            if m.timestamp >= cutoff_time:
                kept.append(m)
            else:
                removed_token_sum += len(m.content.split())
        if len(kept) == len(memories):
            return

        for mem in kept:
            self.remove(mem.id)

    def _remove_lowest_priority_memory(self):
        """删除优先级最低的记忆"""
        memories = self.get_all()
        if not memories:
            return

        # 找到优先级最低的记忆
        lowest_priority = float('inf')
        lowest_memory = None

        for memory in memories:
            priority = self._calculate_priority(memory)
            if priority < lowest_priority:
                lowest_priority = priority
                lowest_memory = memory

        if lowest_memory:
            self.remove(lowest_memory.id)
    
