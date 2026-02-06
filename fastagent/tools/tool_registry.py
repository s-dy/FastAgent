from typing import Any, Callable, Optional

from fastagent.tools.base import Tool, ToolParameter
from fastagent.monitor import monitor_task_status


class ToolRegistry:
    """工具注册表"""
    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._functions: dict[str,dict[str,Any]] = {}

    def register_tool(self, tool:Tool):
        """注册工具"""
        if tool.name in self.tools:
            monitor_task_status(f"⚠️ 警告:工具 '{tool.name}' 已存在，将被覆盖。", level="WARNING")
        self.tools[tool.name] = tool
        monitor_task_status(f"成功注册工具 '{tool.name}'")

    def register_function(self,function:Callable):
        """直接注册函数作为工具"""
        name = function.__name__
        description = function.__doc__ or "无描述"
        if name in self._functions:
            monitor_task_status(f"⚠️ 警告:函数 '{name}' 已存在，将被覆盖。", level="WARNING")
        self._functions[name] = {"description":description,"function":function}
        monitor_task_status(f"成功注册函数 '{name}'")

    def get_tools_description(self) -> str:
        """获取工具描述"""
        descriptions = []
        # Tools
        # Tool对象描述
        for tool in self.tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")

        # 函数工具描述
        for name, info in self._functions.items():
            descriptions.append(f"- {name}: {info['description']}")

        return "\n".join(descriptions) if descriptions else "暂无可用工具"

    def execute_tool(self, tool_name: str, parameters: dict) -> str:
        """执行工具"""
        if tool_name in self.tools:
            return self.tools[tool_name].run(parameters)
        elif tool_name in self._functions:
            return self._functions[tool_name]["function"](**parameters)
        else:
            raise ValueError(f"工具 '{tool_name}' 不存在")

    def get_all_tools(self) -> list[Tool]:
        return list(self.tools.values())

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        if tool_name in self.tools:
            return self.tools[tool_name]
        return None