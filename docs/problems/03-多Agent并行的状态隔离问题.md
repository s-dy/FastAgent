# 问题：多 Agent 并行执行的状态隔离

## 问题描述

系统在 Phase1 和 Phase2 中使用 `ThreadPoolExecutor` 并行执行多个 Agent。并行执行带来了性能提升，但也引入了状态隔离问题：多个 Agent 共享同一个 `ContextManager`，如果设计不当，会导致数据覆盖、消息串扰等并发问题。

## 问题现象

1. **消息历史串扰**：如果多个 Agent 共享同一个 `MessageState`，Agent A 的对话历史会混入 Agent B 的消息，导致 LLM 产生混乱的输出
2. **上下文数据覆盖**：多个 Agent 同时向 `ContextManager` 写入数据时，后写入的数据可能覆盖先写入的数据
3. **工具调用结果错乱**：并行执行时，工具调用的返回结果可能被错误地归属到其他 Agent 的对话流中

## 影响范围

- Phase1：`AttractionSearchAgent` 和 `WeatherQueryAgent` 并行执行
- Phase2：每天的 `DailyAttractionPlanAgent`、`DailyHotelPlanAgent`、`DailyDiningPlanAgent` 三个 Agent 并行执行

## 解决方案

### 1. 独立的 MessageState 实例

每个 Agent 在实例化时创建独立的 `MessageState()`，确保对话历史完全隔离：

```python
# planner.py - Phase1
attraction_agent = AttractionSearchAgent(
    llm=self.llm,
    tool_registry=self.tool_registry,
    context_manager=context_manager,
    state=MessageState(),  # 独立的消息状态
    ...
)
weather_agent = WeatherQueryAgent(
    llm=self.llm,
    tool_registry=self.tool_registry,
    context_manager=context_manager,
    state=MessageState(),  # 独立的消息状态
    ...
)
```

每个 Agent 的 `state` 是独立实例，`EnhancedAgent.run()` 方法中的消息列表构建完全基于各自的 `state`，不会互相干扰。

### 2. ContextManager 的 Key 隔离

`ContextManager` 使用不同的 key 存储不同 Agent 的输出数据，避免覆盖：

```python
# AttractionSearchAgent.run() 中
self.context_manager.share_data(
    "attraction_locations",  # 唯一的 key
    result,
    from_agent=self.name
)

# WeatherQueryAgent.run() 中
self.context_manager.share_data(
    "weather_info",  # 不同的 key
    result,
    from_agent=self.name
)
```

每个 Agent 写入的 key 是预定义的、互不冲突的，读取时也通过明确的 key 获取。

### 3. 线程内独立 Agent 实例

`ThreadPoolExecutor` 的每个线程内创建全新的 Agent 实例，而非共享同一个实例：

```python
# Phase2 - 每天的三个 Agent 都是新创建的实例
with ThreadPoolExecutor(max_workers=3, thread_name_prefix=f"day{day_num}") as executor:
    future_attractions = executor.submit(attraction_plan_agent.run, attraction_prompt)
    future_hotel = executor.submit(hotel_plan_agent.run, hotel_prompt)
    future_dining = executor.submit(dining_plan_agent.run, dining_prompt)
```

Agent 实例在每天的规划循环中重新创建，确保没有跨天的状态残留。

### 4. ContextManager 的请求级隔离

每个 HTTP 请求创建独立的 `ContextManager` 实例，通过 `request_id` 隔离：

```python
# context_manager.py
_context_managers: Dict[str, ContextManager] = {}

def get_context_manager(request_id: str) -> ContextManager:
    if request_id not in _context_managers:
        _context_managers[request_id] = ContextManager(request_id)
    return _context_managers[request_id]
```

不同用户的请求之间完全隔离，不会互相影响。

## 设计权衡

**为什么不使用线程锁？**

`ContextManager` 的 `share_data()` 方法没有加锁，因为：
- Phase1 中两个 Agent 写入的 key 不同（`attraction_locations` vs `weather_info`），不存在写冲突
- Phase2 中三个 Agent 的输出通过 `future.result()` 收集后由主线程统一处理，不直接写入 `ContextManager`
- 避免锁带来的性能开销和死锁风险

## 效果

- 并行执行时无数据串扰，每个 Agent 的输出独立且正确
- Phase1 的执行时间从串行的 ~20s 降低到并行的 ~10s
- Phase2 每天的规划时间从串行的 ~30s 降低到并行的 ~12s
