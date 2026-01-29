import asyncio
import concurrent
from typing import Any, Dict, List

from src.tools.tool_registry import ToolRegistry
from src.monitor import monitor_task_status


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
        result = await loop.run_in_executor(self.executor, _execute)
        return result
    
    async def execute_tools_parallel(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple tools in parallel"""
        tasks = [
            self.execute_tool_async(task["tool_name"], task["parameters"])
            for task in tasks
        ]
        return await asyncio.gather(*tasks)
    
    def __del__(self):
        self.executor.shutdown(wait=True)
