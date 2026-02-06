import asyncio
import concurrent.futures
from typing import Any, Dict, List

from fastagent.monitor import monitor_task_status
from fastagent.tools.tool_registry import ToolRegistry


class AsyncToolExecutor:
    """Async Tool Executor"""

    def __init__(self, tool_registry: ToolRegistry, max_workers: int = 10):
        self.tool_registry = tool_registry
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    async def execute_tool_async(self, tool_name: str, parameters: Dict[str, Any]):
        """Execute tool asynchronously"""
        loop = asyncio.get_event_loop()
        def _execute():
            return self.tool_registry.execute_tool(tool_name, parameters)

        try:
            result = await loop.run_in_executor(self.executor, _execute)
            return result
        except Exception as e:
            monitor_task_status(f"❌ 工具 '{tool_name}' 异步执行失败: {e}",level='ERROR')
            raise Exception(e)
    
    async def execute_tools_parallel(self, tasks: List[Dict[str, Any]]) -> List[dict]:
        """Execute multiple tools in parallel"""
        results = []

        tasks = [
            (task["tool_name"], self.execute_tool_async(task["tool_name"], task["parameters"]))
            for task in tasks
        ]
        for tool_name, task in tasks:
            try:
                result = await task
                results.append({
                    "tool_name": tool_name,
                    "result": result,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "tool_name": tool_name,
                    "result": str(e),
                    "status": "error"
                })
        return results
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)
