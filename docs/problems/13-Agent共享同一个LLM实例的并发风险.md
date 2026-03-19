# 问题：所有 Agent 共享同一个 LLMClient 实例的潜在并发风险

## 问题描述

`PlannerAgent` 在初始化时创建了一个 `LLMClient` 实例（`self.llm`），所有 Agent（Phase1 的搜索 Agent、Phase2 的规划 Agent、Phase3 的主题 Agent）都共享这同一个 `LLMClient` 实例。在并行执行场景下，多个 Agent 同时通过同一个 `LLMClient` 发起 API 调用，可能存在并发安全问题。

## 代码层面的根因

`planner.py` 第 78-79 行：

```python
class PlannerAgent:
    def __init__(self, llm_service: LLMClient, memory_manager: MemoryManager):
        self.llm = llm_service  # 单一实例
```

所有 Agent 创建时都传入同一个 `self.llm`：

```python
# Phase1 - 两个 Agent 并行，共享 self.llm
attraction_agent = AttractionSearchAgent(llm=self.llm, ...)
weather_agent = WeatherQueryAgent(llm=self.llm, ...)

# Phase2 - 每天三个 Agent 并行，共享 self.llm
attraction_plan_agent = DailyAttractionPlanAgent(llm=self.llm, ...)
hotel_plan_agent = DailyHotelPlanAgent(llm=self.llm, ...)
dining_plan_agent = DailyDiningPlanAgent(llm=self.llm, ...)
```

## 潜在风险

### 1. LLMClient 内部状态不线程安全

如果 `LLMClient` 内部维护了请求计数器、速率限制器、连接池等可变状态，多线程并发调用可能导致：
- 计数器不准确
- 速率限制失效
- 连接池竞争

### 2. API 并发限制

通义千问 API 有并发请求数限制。Phase1 中 2 个 Agent + Phase2 中每天 2-3 个 Agent 同时发起请求，加上工具调用型 Agent 的多轮交互，实际并发 API 调用数可能达到 5-8 个，容易触发 API 限流。

### 3. 多请求场景下的并发放大

如果多个用户同时发起行程规划请求，每个请求内部又有多个 Agent 并行执行，并发 API 调用数会成倍增长。

## 解决方案

### 方案一：为每个 Agent 创建独立的 LLMClient

```python
def _create_llm_client(self):
    return LLMClient(
        api_key=self.settings.DASHSCOPE_API_KEY,
        model=self.settings.DASHSCOPE_MODEL_NAME,
        base_url=self.settings.DASHSCOPE_BASE_URL,
    )

# 使用时
attraction_agent = AttractionSearchAgent(
    llm=self._create_llm_client(),  # 独立实例
    ...
)
```

### 方案二：增加全局并发控制

使用信号量限制同时进行的 LLM API 调用数：

```python
import threading

class PlannerAgent:
    # 全局信号量，限制最大并发 API 调用数
    _api_semaphore = threading.Semaphore(3)
    
    def _call_llm_with_limit(self, agent, prompt):
        with self._api_semaphore:
            return agent.run(prompt)
```

### 方案三：确认 LLMClient 的线程安全性

查阅 fastagent 框架文档，确认 `LLMClient.invoke()` 方法是否线程安全。如果是线程安全的（如内部使用了 `httpx` 的线程安全客户端），则共享实例是安全的，只需关注 API 限流问题。
