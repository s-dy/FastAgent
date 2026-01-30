import math
from datetime import datetime
import tiktoken
import jieba


def count_tokens(text: str) -> int:
    """计算文本token数"""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # 降级方案：粗略估算（1 token ≈ 4 字符）
        return len(text) // 4


def calculate_keyword_relevance(query: str, content: str) -> float:
    """关键词匹配

    Args:
        content: 内容
        query: 查询

    Returns:
        float: 相关性分数
    """
    content_words = set(jieba.lcut(content.lower()))
    query_words = set(jieba.lcut(query.lower()))
    if not query_words:
        return 0.0
    if query_words.intersection(content_words):
        return len(query_words) / len(content_words)
    else:
        intersection = content_words & query_words
        union = content_words | query_words
        return (len(intersection) / len(union) if union else 0.0)  * 0.8


def calculate_time_recency(timestamp: datetime,standard: float=24) -> float:
    """计算时间近因性分数
    使用指数衰减模型,指定时间内保持高分,之后逐渐衰减。
    Args:
        timestamp: 时间戳
        standard: 基准时间（小时为单位）

    Returns:
        float: 新近性分数
    """
    age_hours = (datetime.now() - timestamp).total_seconds() / 3600
    decay_factor = 0.1 # 衰减系数
    recency_score = math.exp(-decay_factor * age_hours / standard)
    return max(0.1, min(1.0, recency_score))