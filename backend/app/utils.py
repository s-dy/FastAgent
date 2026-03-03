import asyncio


def _run_async(coroutine):
    """
    在同步上下文中运行异步协程。
    如果当前线程已有事件循环在运行，则创建新线程执行；否则直接 asyncio.run()。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 当前已在异步事件循环中（如 FastAPI），使用新线程
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coroutine)
            return future.result()
    else:
        return asyncio.run(coroutine)