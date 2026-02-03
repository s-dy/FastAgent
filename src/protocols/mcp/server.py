from typing import Dict, Any, Optional, Callable, Literal
from fastmcp import FastMCP


class MCPServer:
    """基于 fastmcp 库的 MCP 服务器"""

    def __init__(
            self,
            name: str,
            description: Optional[str] = None
    ):
        """
        初始化 MCP 服务器

        Args:
            name: 服务器名称
            description: 服务器描述
        """
        self.mcp = FastMCP(name=name)
        self.name = name
        self.description = description or f"{name} MCP Server"

    def add_tool(
            self,
            func: Callable,
            name: Optional[str] = None,
            description: Optional[str] = None
    ):
        """
        添加工具到服务器

        Args:
            func: 工具函数
            name: 工具名称（可选，默认使用函数名）
            description: 工具描述（可选，默认使用函数文档字符串）
        """
        # 使用装饰器注册工具
        if name or description:
            self.mcp.tool(name=name, description=description)(func)
        else:
            self.mcp.tool()(func)

    def add_resource(
            self,
            func: Callable,
            uri: str,
            name: Optional[str] = None,
            description: Optional[str] = None
    ):
        """
        添加资源到服务器

        Args:
            func: 资源处理函数
            uri: 资源 URI
            name: 资源名称（可选）
            description: 资源描述（可选）
        """
        # 使用装饰器注册资源
        self.mcp.resource(uri,name=name,description=description)(func)

    def add_prompt(
            self,
            func: Callable,
            name: Optional[str] = None,
            description: Optional[str] = None
    ):
        """
        添加提示词模板到服务器

        Args:
            func: 提示词生成函数
            name: 提示词名称（可选）
            description: 提示词描述（可选）
        """
        # 使用装饰器注册提示词
        if name or description:
            self.mcp.prompt(name=name, description=description)(func)
        else:
            self.mcp.prompt()(func)

    def run(self, transport: Literal["stdio", "http", "sse", "streamable-http"] = "stdio", **kwargs):
        """运行服务器

        Args:
            transport: 传输方式 ("stdio", "http", "sse", "streamable-http")
            **kwargs: 传输特定的参数
                - host: HTTP 服务器主机（默认 "127.0.0.1"）
                - port: HTTP 服务器端口（默认 8000）
                - 其他 FastMCP.run() 支持的参数
        """
        self.mcp.run(transport=transport, **kwargs)

    def get_info(self) -> Dict[str, Any]:
        """
        获取服务器信息

        Returns:
            服务器信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "protocol": "MCP"
        }
