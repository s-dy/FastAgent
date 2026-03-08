"""
MCP 调用结果缓存服务

基于 Redis 缓存 MCP 工具调用的返回结果，避免重复调用外部 API。
不同类型的工具设置不同的过期时间：
- 天气查询：1 小时（天气变化快）
- 景点搜索 / 酒店搜索 / 餐厅搜索：24 小时
- 景点详情：72 小时（基本不变）
"""

import json
import hashlib
from typing import Any, Optional, Dict

from app.observability.logger import default_logger as logger
from app.config import settings

# 各工具的缓存过期时间（秒）
TOOL_CACHE_TTL: Dict[str, int] = {
    "maps_weather": 1 * 60 * 60,           # 天气：1 小时
    "maps_text_search": 24 * 60 * 60,      # 景点搜索：24 小时
    "maps_search_detail": 72 * 60 * 60,    # 景点详情：72 小时
}

# 默认过期时间：12 小时
DEFAULT_CACHE_TTL = 12 * 60 * 60

# 缓存 Key 前缀
CACHE_KEY_PREFIX = "mcp_cache"


class McpCacheService:
    """
    MCP 工具调用结果的 Redis 缓存服务。

    通过 tool_name + tool_args 生成唯一缓存 Key，
    在工具调用前检查缓存，命中则直接返回，未命中则调用后写入缓存。
    """

    def __init__(self):
        self._redis_client = None

    def _get_redis(self):
        """延迟获取 Redis 客户端，避免模块加载时连接失败"""
        if self._redis_client is None:
            from app.services.redis_service import redis_service
            self._redis_client = redis_service.redis
        return self._redis_client

    @staticmethod
    def _build_cache_key(tool_name: str, tool_args: dict) -> str:
        """
        根据工具名和参数生成唯一的缓存 Key。

        Key 格式: mcp_cache:{tool_name}:{args_hash}
        args_hash 使用参数的 JSON 序列化（key 排序）后取 MD5。
        """
        args_json = json.dumps(tool_args, sort_keys=True, ensure_ascii=False)
        args_hash = hashlib.md5(args_json.encode("utf-8")).hexdigest()
        return f"{CACHE_KEY_PREFIX}:{tool_name}:{args_hash}"

    @staticmethod
    def _get_ttl(tool_name: str) -> int:
        """获取指定工具的缓存过期时间"""
        return TOOL_CACHE_TTL.get(tool_name, DEFAULT_CACHE_TTL)

    def get_cached_result(self, tool_name: str, tool_args: dict) -> Optional[Any]:
        """
        查询缓存，命中则返回反序列化后的结果，未命中返回 None。

        Args:
            tool_name: MCP 工具名称
            tool_args: 工具调用参数

        Returns:
            缓存的工具调用结果，未命中返回 None
        """
        if not settings.MCP_CACHE_ENABLED:
            return None

        try:
            redis_client = self._get_redis()
            cache_key = self._build_cache_key(tool_name, tool_args)
            cached_value = redis_client.get(cache_key)

            if cached_value is not None:
                result = json.loads(cached_value)
                logger.info(f"🎯 [McpCache] 缓存命中: {tool_name}({tool_args})")
                return result

            return None
        except Exception as cache_error:
            logger.warning(f"⚠️ [McpCache] 读取缓存失败: {cache_error}")
            return None

    def set_cached_result(self, tool_name: str, tool_args: dict, result: Any) -> None:
        """
        将工具调用结果写入缓存。

        Args:
            tool_name: MCP 工具名称
            tool_args: 工具调用参数
            result: 工具调用的返回结果
        """
        if not settings.MCP_CACHE_ENABLED:
            return

        try:
            redis_client = self._get_redis()
            cache_key = self._build_cache_key(tool_name, tool_args)
            ttl = self._get_ttl(tool_name)
            serialized = json.dumps(result, ensure_ascii=False)

            redis_client.setex(cache_key, ttl, serialized)
            logger.info(
                f"💾 [McpCache] 缓存写入: {tool_name}({tool_args}), "
                f"TTL={ttl // 3600}h{(ttl % 3600) // 60}m"
            )
        except Exception as cache_error:
            logger.warning(f"⚠️ [McpCache] 写入缓存失败: {cache_error}")

    def invalidate(self, tool_name: str, tool_args: dict) -> bool:
        """手动失效指定缓存"""
        try:
            redis_client = self._get_redis()
            cache_key = self._build_cache_key(tool_name, tool_args)
            deleted = redis_client.delete(cache_key)
            return deleted > 0
        except Exception as cache_error:
            logger.warning(f"⚠️ [McpCache] 删除缓存失败: {cache_error}")
            return False

    def invalidate_by_tool(self, tool_name: str) -> int:
        """批量失效某个工具的所有缓存"""
        try:
            redis_client = self._get_redis()
            pattern = f"{CACHE_KEY_PREFIX}:{tool_name}:*"
            deleted_count = 0
            for key in redis_client.scan_iter(match=pattern, count=100):
                redis_client.delete(key)
                deleted_count += 1
            if deleted_count > 0:
                logger.info(f"🗑️ [McpCache] 批量清除 {tool_name} 缓存: {deleted_count} 条")
            return deleted_count
        except Exception as cache_error:
            logger.warning(f"⚠️ [McpCache] 批量删除缓存失败: {cache_error}")
            return 0


# 全局单例
mcp_cache_service = McpCacheService()
