# 问题：所有工具调用型 Agent 共享同一个 ToolRegistry 和 MCP 连接

## 问题描述

`PlannerAgent` 在初始化时创建了一个 `ToolRegistry` 实例并注册了高德地图 MCP 工具，所有需要工具调用的 Agent 都共享这同一个 `ToolRegistry`。在并行执行场景下，多个 Agent 同时通过同一个 MCP 连接发起工具调用，可能导致连接竞争和响应混乱。

## 代码层面的根因

`planner.py` 第 83-88 行：

```python
self.tool_registry = ToolRegistry()
self.tool_registry.register_tool(MCPTool(
    name="amap",
    description="高德地图服务",
    server_command=f"https://mcp.amap.com/mcp?key={os.getenv('AMAP_MCP_KEY')}",
))
```

Phase1 中 `AttractionSearchAgent` 和 `WeatherQueryAgent` 并行执行，都通过 `self.tool_registry` 调用高德 MCP 工具。Phase2 中 `DailyHotelPlanAgent` 也使用同一个 `self.tool_registry`。

## 潜在风险

### 1. MCP 连接的并发安全

MCP 协议基于 HTTP/SSE 通信。如果 `MCPTool` 内部维护了单一的 HTTP 连接或会话状态，多线程并发调用可能导致：
- 请求和响应的错位（Agent A 收到 Agent B 的工具调用结果）
- 连接被意外关闭
- 请求超时

### 2. API Key 的速率限制

所有 Agent 共享同一个高德 API Key，并发调用可能触发高德 API 的速率限制（QPS 限制），导致部分工具调用失败。

### 3. Phase1 和 Phase2 的工具调用冲突

Phase1 的景点搜索和天气查询并行执行时，同时发起 MCP 工具调用。如果 Phase2 的酒店搜索也在进行（虽然当前是串行的），并发压力更大。

## 解决方案

### 方案一：为每个 Agent 创建独立的 ToolRegistry

```python
def _create_tool_registry(self):
    registry = ToolRegistry()
    registry.register_tool(MCPTool(
        name="amap",
        description="高德地图服务",
        server_command=f"https://mcp.amap.com/mcp?key={os.getenv('AMAP_MCP_KEY')}",
    ))
    return registry

# Phase1
attraction_agent = AttractionSearchAgent(
    tool_registry=self._create_tool_registry(),  # 独立实例
    ...
)
```

### 方案二：增加工具调用的并发控制

在 `EnhancedAgent` 基类中增加工具调用的并发限制：

```python
class EnhancedAgent(ReactAgent):
    _tool_call_semaphore = threading.Semaphore(2)  # 最多 2 个并发工具调用
    
    def _execute_tool_call(self, tool_name, tool_arguments):
        with self._tool_call_semaphore:
            return super()._execute_tool_call(tool_name, tool_arguments)
```

### 方案三：MCP 连接池

实现 MCP 连接池，为每个并发的工具调用分配独立的连接：

```python
class MCPConnectionPool:
    def __init__(self, max_connections=5):
        self.pool = queue.Queue(maxsize=max_connections)
        for _ in range(max_connections):
            self.pool.put(self._create_connection())
    
    def acquire(self):
        return self.pool.get()
    
    def release(self, conn):
        self.pool.put(conn)
```
