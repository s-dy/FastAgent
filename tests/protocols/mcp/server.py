#!/usr/bin/env python3
"""
示例 MCP 服务器
用于测试 MCP 客户端功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from fastagent.protocols.mcp.server import MCPServer


def create_example_server() -> MCPServer:
    """创建一个示例 MCP 服务器"""
    server = MCPServer(
        name="example-server",
        description="A simple example MCP server with calculator and greeting tools"
    )

    # 添加一个简单的计算器工具
    def calculator(expression: str) -> str:
        """计算数学表达式

        Args:
            expression: 要计算的数学表达式，例如 "2 + 2" 或 "10 * 5"
        """
        try:
            # 安全的表达式求值（仅支持基本运算）
            allowed_chars = set("0123456789+-*/() .")
            if not all(c in allowed_chars for c in expression):
                return f"Error: Invalid characters in expression"
            result = eval(expression)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

    server.add_tool(calculator, name="calculator", description="Calculate a mathematical expression")

    # 添加一个问候工具
    def greet(name: str) -> str:
        """生成友好的问候语

        Args:
            name: 要问候的人的名字
        """
        return f"Hello, {name}! Welcome to the MCP server example."

    server.add_tool(greet, name="greet", description="Generate a friendly greeting")

    return server


if __name__ == "__main__":
    # 创建并运行示例服务器
    server = create_example_server()
    print(f"🚀 Starting {server.name}...")
    print(f"📝 {server.description}")
    print(f"🔌 Protocol: MCP")
    print(f"📡 Transport: stdio")
    print()
    server.run(transport='stdio')