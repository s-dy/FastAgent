from dataclasses import dataclass


@dataclass
class ContextConfig:
    """上下文配置"""
    max_tokens: int = 8000  # 总预算
    reserve_ratio: float = 0.15  # 生成余量（10-20%）
    min_relevance: float = 0.3  # 最小相关性阈值

    enable_compression: bool = True  # 启用压缩

    # 计算属性
    max_conversation_history: int = 10
    text_relevance_weight: float = 0.7 # 文本相关性权重
    time_recency_weight: float = 0.3 # 时间新近性权重


    def get_available_tokens(self) -> int:
        """获取可用token预算"""
        return int(self.max_tokens * (1 - self.reserve_ratio))
