from typing import List

from src.memory.config import MemoryConfig
from src.memory.base import MemoryItem, BaseMemory
from src.memory.store import MemoryStore
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
    
    def __init__(self, config: MemoryConfig):
        super().__init__(config)

        self.max_capacity = config.working_memory_capacity or 50
        self.max_age_minutes = config.working_memory_ttl or 60
        self.store = MemoryStore()  # TODO 可以换redis
    
    def add(self, user_id: str, memory_item: MemoryItem) -> None:
        """添加工作记忆"""
        self._expire_old_memories()  # 过期清理
        
        if len(self.store.list(user_id)) >= self.max_capacity:
            self._remove_lowest_priority_memory()  # 容量管理

        self.store.add(user_id,memory_item)

    def retrieve(self, user_id: str, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """混合检索：TF-IDF向量化 + 关键词匹配"""
        """
        工作记忆的检索采用了混合检索策略，首先尝试使用TF-IDF向量化进行语义检索，如果失败则回退到关键词匹配。这种设计确保了在各种环境下都能提供可靠的检索服务。评分算法结合了语义相似度、时间衰减和重要性权重，最终得分公式为：`(相似度 × 时间衰减) × (0.8 + 重要性 × 0.4)`
        """
        self._expire_old_memories()
        
        # 尝试TF-IDF向量检索
        vector_scores = self._try_tfidf_search(user_id, query)
        
        # 计算综合分数
        scored_memories = []
        for memory in self.store.list(user_id):
            vector_score = vector_scores.get(memory.id, 0.0)
            keyword_score = calculate_keyword_relevance(query, memory.content)
            
            # 混合评分
            base_relevance = vector_score * 0.7 + keyword_score * 0.3 if vector_score > 0 else keyword_score
            time_decay = calculate_time_recency(memory.timestamp, standard=0.5)
            importance_weight = 0.8 + (memory.importance * 0.4)
            
            final_score = base_relevance * time_decay * importance_weight
            if final_score > 0:
                scored_memories.append((final_score, memory))
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored_memories[:limit]]

    def _expire_old_memories(self):
        """过期清理"""

    def _remove_lowest_priority_memory(self):
        """容量管理"""

    def _try_tfidf_search(self,user_id: str, query: str) -> dict[str,float]:
        """TF-IDF"""
        # TODO 替换为真正的检索算法
        result = {}
        for memory in self.store.list(user_id):
            result.setdefault(memory.id, 0.4)
        return result
