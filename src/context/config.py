from dataclasses import dataclass


@dataclass
class ContextConfig:
    """上下文配置"""
    max_tokens: int = 1024 # 最大令牌数
    reserve_ratio: float = 0.2 # 保留比例
    min_relevance: float = 0.1 # 最小相关性
    enable_compression: bool = True # 是否启用压缩
    recency_weight: float = 0.3 # 时间近因性权重
    relevance_weight: float = 0.7 # 相关性权重

    def __post_init__(self):
        assert self.reserve_ratio >= 0 and self.reserve_ratio <= 1, "保留比例必须在0到1之间"
        assert self.min_relevance >= 0 and self.min_relevance <= 1, "最小相关性必须在0到1之间"
        assert abs(self.recency_weight + self.relevance_weight - 1) < 1e-6, "时间近因性权重和相关性权重之和必须等于1"
