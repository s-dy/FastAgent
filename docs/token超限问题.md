# Token 超限问题及解决方案

## 问题描述

当用户规划的旅行天数较多时（≥5 天），行程规划专家（`PlannerAgent`）最终输出的结果会超过 LLM 的 `max_output_tokens` 限制，导致 JSON 输出被截断、解析失败，行程规划无法正常完成。

### 根本原因

原有架构中，所有规划逻辑集中在一个 `EnhancedPlannerAgent` 上，它需要**一次性输出整个行程的完整 JSON**，包含每天的景点（含经纬度、图片URL、描述）、酒店、餐饮、预算等信息。

**Token 膨胀分析：**

| 维度 | 单天输出量 | 7天行程总输出量 |
|---|---|---|
| 景点（3个/天，含经纬度、描述等） | ~800 token | ~5600 token |
| 酒店（1个/天） | ~200 token | ~1400 token |
| 餐饮（3个/天） | ~400 token | ~2800 token |
| 预算 + 主题 + 天气 | ~200 token | ~1400 token |
| **合计** | **~1600 token** | **~11200 token** |

加上系统提示词（~3000 token）和输入的景点/酒店/天气原始数据，总 token 量轻松超过大多数模型的输出上限。

### 附带问题

1. **提示词与模型字段不一致**：`PLANNER_AGENT_PROMPT` 中定义的 JSON Schema 字段名（如 `lat/lng`、`dinings`、`suggested_duration_hours`）与 `app/models/common.py` 中的 Pydantic 模型字段名（如 `latitude/longitude`、`dining`、`visit_duration`）不一致，导致 `model_validate` 解析频繁失败。
2. **预算计算不准确**：让 LLM 计算预算总和容易出错。
3. **错误不可隔离**：一次性生成整个行程，任何一天的数据异常都会导致整个 JSON 解析失败。

---

## 解决方案：分治 + 按天规划

### 核心思路

> 将"一次性生成完整行程"改为"按天分步生成"，每个专业 Agent 只负责单天单维度的结构化输出，最后由协调器程序化拼装。

### 架构改造

**改造前：**
```
PlannerAgent (协调器)
  ├── AttractionSearchAgent  → 搜索景点
  ├── HotelSearchAgent       → 搜索酒店
  ├── WeatherQueryAgent      → 查询天气
  └── EnhancedPlannerAgent   → 一次性输出完整行程 JSON（Token 瓶颈）
```

**改造后：**
```
PlannerAgent (协调器)
  │
  │  Phase1: 并行信息收集
  ├── AttractionSearchAgent  → 搜索景点原始数据
  ├── WeatherQueryAgent      → 查询天气原始数据
  │
  │  Phase2: 按天循环规划（每天并行）
  │  for each day:
  │    ├── DailyAttractionPlanAgent → 为当天分配景点（输出 JSON 数组）
  │    ├── DailyHotelPlanAgent     → 动态搜索当天景点附近酒店（带工具调用）
  │    └── DailyDiningPlanAgent    → 为当天推荐餐饮（输出 JSON 数组）
  │
  │  Phase3: 程序化拼装
  ├── TripThemeAgent → 生成标题和每天主题
  └── 协调器 → 计算预算 + 地理验证 + 拼装 TripPlanResponse
```

### 关键改动

#### 1. 新增按天规划 Agent（`app/agents/agents.py`）

| Agent | 职责 | 工具调用 | 单次输出 Token |
|---|---|---|---|
| `DailyAttractionPlanAgent` | 从候选景点中为单天挑选 2~4 个景点 | 否 | ~500-800 |
| `DailyHotelPlanAgent` | 根据当天景点位置**动态搜索**附近酒店 | **是**（高德 MCP） | ~200-300 |
| `DailyDiningPlanAgent` | 为单天推荐早/午/晚餐 | 否 | ~300-500 |
| `TripThemeAgent` | 为整个行程生成标题和每天主题 | 否 | ~200 |

#### 2. 统一提示词与 Pydantic 模型字段名

所有按天规划 Agent 的提示词中，JSON Schema 字段名严格对齐 `app/models/common.py`：

| 改造前（提示词） | 改造后（提示词） | Pydantic 模型 |
|---|---|---|
| `location.lat / lng` | `location.longitude / latitude` | `Location.longitude / latitude` |
| `suggested_duration_hours` | `visit_duration`（分钟） | `Attraction.visit_duration` |
| `dinings` | `dining` | `DailyPlan.dining` |
| `cost_per_person` | `estimated_cost` | `Meal.estimated_cost` |
| `ticket_price`（字符串） | `ticket_price`（整数） | `Attraction.ticket_price` |

#### 3. 预算计算程序化（`app/agents/planner.py`）

不再让 LLM 计算预算，而是在 Python 代码中根据各 Agent 输出的结构化数据程序化累加：

```python
def _calculate_daily_budget(self, attractions_data, hotel_data, dining_data, budget_level):
    attraction_ticket_cost = sum(a.get("ticket_price", 0) for a in attractions_data)
    hotel_cost = hotel_data.get("estimated_cost", 0)
    dining_cost = sum(m.get("estimated_cost", 0) for m in dining_data)
    transport_cost = TRANSPORT_COST_PER_DAY.get(budget_level, 60.0)
    total = attraction_ticket_cost + hotel_cost + dining_cost + transport_cost
    return Budget(...)
```

#### 4. 酒店搜索动态化

酒店搜索从"Phase1 提前搜索全城候选列表"优化为"Phase2 根据当天景点位置动态搜索附近酒店"：

- `DailyHotelPlanAgent` 启用工具调用（`enable_tool_calling=True`），接收 `tool_registry`
- 每天规划时，先完成景点分配，再将景点经纬度传给酒店 Agent，由它自行搜索附近酒店

#### 5. 工具调用防无限循环（`app/agents/enhanced_agent.py`）

增加两层防护机制，防止 LLM 无限循环调用工具：

- **引导总结**：工具调用次数达到阈值后，追加 user 消息引导 LLM 总结结果
- **强制禁止**：最后一次迭代时设置 `tool_choice="none"`，从 API 层面禁止工具调用

---

## 优化效果

| 维度 | 改造前 | 改造后 |
|---|---|---|
| **单次 LLM 输出** | 整个行程 JSON（7天 ≈ 11000+ token） | 单天单维度（≈ 500~800 token） |
| **天数扩展性** | 5天以上容易超限 | 无限制，逐天生成 |
| **错误隔离** | 一次失败全部失败 | 某天某 Agent 失败不影响其他天 |
| **预算准确性** | LLM 计算，容易出错 | 程序化计算，100% 准确 |
| **酒店推荐精准度** | 全城搜索，可能离景点远 | 按天动态搜索景点附近酒店 |
| **字段一致性** | 提示词与模型不一致，解析常失败 | 严格对齐，解析稳定 |