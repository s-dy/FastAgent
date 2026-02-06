import asyncio

from fastagent.tools import ToolRegistry, AsyncToolExecutor


async def demo_parallel_execution():
    """演示并行执行的示例"""

    # 创建注册表（这里假设已经注册了工具）
    registry = ToolRegistry()

    # 定义并行任务
    tasks = [
        {"tool_name": "my_calculator", "parameters": "2 + 2"},
        {"tool_name": "my_calculator", "parameters": "3 * 4"},
        {"tool_name": "my_calculator", "parameters": "sqrt(16)"},
        {"tool_name": "my_calculator", "parameters": "10 / 2"},
    ]

    # 并行执行
    with AsyncToolExecutor(tool_registry=registry, max_workers=10) as executor:
        results = await executor.execute_tools_parallel(tasks)

    # 显示结果
    print("\n📊 并行执行结果:")
    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{status_icon} {result['tool_name']} = {result['result']}")

    return results


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_parallel_execution())