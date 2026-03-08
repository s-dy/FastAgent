from typing import List, Callable

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.observability.logger import default_logger as logger
from app.services.mcp_cache_service import mcp_cache_service
from app.utils import _run_async

class ToolsManager:
    """工具管理器"""
    _instance: 'ToolsManager' = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if ToolsManager._initialized:
            return
        ToolsManager._initialized = True
        self.tools: dict[str, BaseTool] = {}

    def add_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> BaseTool:
        return self.tools[tool_name]

    def get_tools(self) -> List[BaseTool]:
        return list(self.tools.values())

    def get_tool_names(self) -> List[str]:
        return list(self.tools.keys())

    def register_tools(self, source: MultiServerMCPClient | BaseTool):
        if isinstance(source, MultiServerMCPClient):
            for name, connection in source.connections.items():
                tools = _run_async(source.get_tools(server_name=name))
                if name == 'amap':
                    tools = list(filter(lambda tool: tool.name in ('maps_search_detail', 'maps_text_search', 'maps_weather'), tools))
                for tool in tools:
                    self.add_tool(tool)
        elif isinstance(source, BaseTool):
            self.add_tool(source)

    def call_tool(self, tool_name: str, tool_args: dict, parser: Callable = None, tool_call_id: str = None) -> ToolMessage:
        if not tool_call_id:
            from uuid import uuid4
            tool_call_id = str(uuid4().hex)

        tool = self.get_tool(tool_name)
        if not tool:
            error_message = f"工具 '{tool_name}' 不存在"
            logger.warning(f"⚠️ {error_message}")
            return ToolMessage(
                content=error_message,
                tool_call_id=tool_call_id,
            )

        # 检查 Redis 缓存：用原始参数作为缓存 Key
        cached_result = mcp_cache_service.get_cached_result(tool_name, tool_args)
        if cached_result is not None:
            # 缓存命中：如果调用方提供了 parser，对缓存的原始数据重新执行 parser
            if parser:
                cached_result = parser(cached_result)
            return ToolMessage(
                content=cached_result,
                tool_call_id=tool_call_id,
            )

        # 缓存未命中：实际调用 MCP 工具
        try:
            tool_result = _run_async(tool.ainvoke(tool_args))

            # 先将原始结果写入缓存（parser 之前），保证缓存的是通用数据
            mcp_cache_service.set_cached_result(tool_name, tool_args, tool_result)

            if parser:
                tool_result = parser(tool_result)
            logger.info(f"  ✅ 工具 '{tool_name}' 执行成功")
        except Exception as tool_error:
            tool_result = f"工具执行失败: {tool_error}"
            logger.error(f"  ❌ 工具 '{tool_name}' 执行失败: {tool_error}")

        return ToolMessage(
            content=tool_result,
            tool_call_id=tool_call_id,
        )
