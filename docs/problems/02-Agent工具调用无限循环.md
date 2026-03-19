# 问题：Agent 工具调用无限循环

## 问题描述

搜索类 Agent（`AttractionSearchAgent`、`WeatherQueryAgent`、`DailyHotelPlanAgent`）采用 ReAct 模式，LLM 可以自主决定是否调用工具。但在实际运行中，LLM 经常陷入"无限工具调用"循环——不断调用搜索工具获取更多数据，但始终不输出最终的总结结果。

## 问题现象

1. **反复搜索同一关键词**：LLM 用不同的关键词反复搜索同一类信息，如先搜"北京景点"，再搜"北京旅游景点"，再搜"北京热门景点"
2. **搜索结果不满意后继续搜索**：LLM 认为搜索结果不够丰富，持续调用工具尝试获取更多数据
3. **超时导致请求失败**：工具调用循环导致单个 Agent 执行时间超过 120 秒的超时限制

## 影响范围

- Phase1 的景点搜索和天气查询 Agent
- Phase2 的酒店推荐 Agent（改造为工具调用型后新增此问题）
- 严重时导致整个行程规划请求超时失败

## 根因分析

ReAct 模式下，LLM 的行为由 System Prompt 和对话历史共同决定。当 System Prompt 中只说"使用工具搜索"但没有明确"何时停止搜索"时，LLM 倾向于追求更完美的搜索结果，导致循环。

## 解决方案

在 `EnhancedAgent` 基类（`enhanced_agent.py`）中实现了 **三层防护机制**：

### 第一层：迭代次数硬上限（`max_step`）

```python
while current_iteration < self.max_step:
    current_iteration += 1
    # ... LLM 调用和工具执行 ...
```

`max_step` 是 ReactAgent 基类的配置参数，设置了 LLM 交互的最大轮次。超过此限制后循环强制退出。

### 第二层：工具调用阈值 + 引导消息

```python
# 工具调用次数阈值：超过此次数后引导 LLM 总结结果
summarize_threshold = max(1, self.max_step - 2)

# 在工具执行后检查
if tool_call_count >= summarize_threshold:
    messages.append({
        "role": "user",
        "content": "你已经获取了足够的信息，请不要再调用工具，"
                   "直接根据已有的工具返回结果进行总结并输出最终回答。",
    })
```

当工具调用次数达到 `max_step - 2` 时，向对话历史中注入一条引导消息，明确告诉 LLM "停止调用工具，开始总结"。这利用了 LLM 遵循指令的特性，在大多数情况下能有效终止循环。

### 第三层：强制禁止工具调用

```python
# 当接近最大迭代次数时，强制禁止工具调用
current_tool_choice = tool_choice
if current_iteration >= self.max_step:
    current_tool_choice = "none"

response = self.llm.invoke(
    messages,
    tools=tool_schemas,
    tool_choice=current_tool_choice,  # "none" 禁止工具调用
    **kwargs,
)
```

在最后一次迭代时，将 `tool_choice` 设置为 `"none"`，从 API 层面禁止 LLM 调用任何工具，强制其输出纯文本响应。

### 兜底措施

```python
if current_iteration >= self.max_step and not final_response:
    final_response = "抱歉，我无法在限定步数内完成这个任务。"
```

如果三层防护都未能获得有效响应，返回一个友好的兜底消息，避免返回空结果。

## 效果

- Agent 的平均执行时间从不可控（可能超过 120s）稳定在 10-30s
- 工具调用次数从不可控（可能 10+ 次）控制在 3-5 次
- 消除了因工具调用循环导致的请求超时问题

## 补充：Prompt 层面的配合

在搜索类 Agent 的 System Prompt 中也增加了明确的停止指令：

```
搜索完成后，总结信息
```

双管齐下（Prompt 引导 + 代码强制），确保工具调用行为可控。
