import asyncio
import concurrent.futures
from typing import Coroutine

from src.monitor import monitor_task_status


def run_async_event(coroutine:Coroutine):
    # 运行异步操作
    try:
        # 检查是否已有运行中的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行中的循环，在新线程中运行新的事件循环
            def run_in_thread():
                # 在新线程中创建新的事件循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coroutine)
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        except RuntimeError:
            # 没有运行中的循环，直接运行
            return asyncio.run(coroutine)
    except Exception as e:
        monitor_task_status(f"异步操作失败: {str(e)}")
        raise e
