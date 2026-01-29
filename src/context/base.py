from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ContextPacket:
    """候选信息包"""
    content: str # 内容
    timestamp: datetime # 时间戳
    token_count: int # 令牌计数
    relevance_score: float = 0.5 # 相关性评分
    metadata: Optional[dict] = None # 元数据

    def __post_init__(self):
        """初始化后处理"""
        if not self.metadata:
            self.metadata = {}
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))
