# 🧳 智能旅行助手 (TravelAgent)

基于**多智能体协作架构**的智能旅行规划系统。用户输入目的地、日期、偏好等信息，系统通过多个专业 AI Agent 协作，自动生成包含景点、餐饮、酒店和预算的完整行程计划。

## ✨ 核心功能

- **智能行程规划**：输入目的地、日期、偏好，自动生成包含景点、餐饮、酒店的完整行程
- **多智能体协作**：6 个专业 Agent 各司其职，通过三阶段流水线协作完成规划
- **按天分步生成**：采用分治策略逐天规划，支持任意天数的行程，无 Token 超限问题
- **实时工具调用**：集成高德地图 MCP，实时搜索景点、酒店、天气等信息
- **程序化预算计算**：门票、酒店、餐饮、交通费用自动累加，100% 准确
- **地理位置验证**：自动校验景点/酒店是否在目标城市范围内，过滤异常数据
- **用户记忆系统**：记住用户历史偏好，个性化推荐
- **结构化日志**：JSON 格式日志 + 请求 ID 追踪，便于问题排查

---

## 🏗️ 系统架构

### 三阶段规划流水线 → 协调器-工作器架构

```
┌─────────────────────────────────────────────────────────────┐
│                  OrchestratorWorkerPlanner                   │
│                  (协调器-工作器架构)                           │
│                                                             │
│  基于 LangGraph 的 Send API 实现动态任务调度                  │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  Orchestrator (协调器)                       │          │
│  │  - 任务分解与委派                             │          │
│  │  - 动态生成 TripSection                      │          │
│  │  - 管理任务依赖关系                           │          │
│  └──────────────┬───────────────────────────────┘          │
│                 │ Send API (动态节点创建)                    │
│                 ▼                                           │
│  ┌──────────────────────────────────────────────┐          │
│  │  Workers (工作节点，并行执行)                 │          │
│  │                                              │          │
│  │  景点搜索 Worker (高德 MCP)                   │          │
│  │  天气查询 Worker (高德 MCP)                   │          │
│  │  每日规划 Worker (多个实例，每天一个)          │          │
│  └──────────────┬───────────────────────────────┘          │
│                 │                                           │
│                 ▼                                           │
│  ┌──────────────────────────────────────────────┐          │
│  │  Synthesizer (合成器)                        │          │
│  │  - 汇总所有工作节点结果                       │          │
│  │  - 生成标题和主题                             │          │
│  │  - 计算总预算                                │          │
│  │  - 验证相邻天行程                             │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 各阶段详解

| 阶段 | 说明 | 执行方式 |
|------|------|---------|
| **阶段1** | 并行搜索景点和天气原始数据 | Send API 创建 2 个 Worker 并行执行 |
| **阶段2** | 每日规划（景点、酒店、餐饮） | Send API 创建 N 个 Worker 并行执行（N=天数） |
| **阶段3** | 拼装验证 | Synthesizer 顺序执行 |

---

## 🤖 Agent 角色设计

系统采用**协调器-工作器架构**，包含以下核心组件：

### 协调器（Orchestrator）

- **职责**：任务分解、动态生成 TripSection、管理任务依赖关系
- **输入**：CoordinatorState（包含请求信息、已完成任务等）
- **输出**：TripSection 列表（待执行的任务）
- **特点**：根据执行进度动态调整任务分配策略

### 工作节点（Workers）

| 组件 | 职责 | 工具调用 | 说明 |
|-------|------|---------|------|
| **AttractionSearchWorker** | 搜索景点 POI | 是（高德 MCP） | 返回原始景点数据 |
| **WeatherSearchWorker** | 查询天气预报 | 是（高德 MCP） | 返回行程期间天气数据 |
| **DailyPlanningWorker** | 规划单日行程 | 是（高德 MCP） | 包含景点、酒店、餐饮规划 |

### 合成器（Synthesizer）

- **职责**：汇总结果、生成标题主题、计算总预算、验证相邻天行程
- **输入**：所有工作节点的 completed_tasks
- **输出**：TripPlanResponse（最终行程计划）

### 核心特性

- **Send API 动态节点创建**：运行时动态创建工作节点实例
- **状态共享与聚合**：通过 `operator.add` reducer 自动合并工作节点结果
- **并行执行**：所有工作节点并行运行，大幅提升效率
- **任务依赖管理**：通过条件边自动管理任务间的依赖关系

详细设计文档见：[`docs/多智能体设计.md`](../docs/多智能体设计.md)

---

## 📁 项目结构

```
TravelAgent/
├── main.py                              # 应用入口（待实现）
├── pyproject.toml                       # 项目依赖配置
├── .env                                 # 环境变量（API Key 等）
│
├── app/
│   ├── config.py                        # 应用配置（Pydantic Settings）
│   │
│   ├── agents/                          # 智能体模块
│   │   ├── agents.py                    # 6 个专业 Agent 定义 + 提示词
│   │   ├── enhanced_agent.py            # Agent 基类（记忆/上下文/防循环）
│   │   └── planner.py                   # 协调器（三阶段规划流水线）
│   │
│   ├── models/                          # 数据模型
│   │   ├── __init__.py                  # 统一导出
│   │   ├── common.py                    # 基础模型（Location/Attraction/Hotel/Meal/Budget）
│   │   └── trip.py                      # 行程模型（TripPlanRequest/Response/DailyPlan）
│   │
│   ├── services/                        # 服务层
│   │   └── context_manager.py           # 上下文管理器（Agent 间数据共享）
│   │
│   └── observability/                   # 可观测性
│       ├── __init__.py
│       └── logger.py                    # 结构化日志系统
│
├── tests/
│   └── test_planer.py                   # 规划器测试
│
├── docs/
│   └── token超限问题.md                  # Token 超限问题分析与解决方案
│
└── logs/                                # 日志输出目录
    ├── app.log                          # 全量日志（JSON 格式）
    └── error.log                        # 错误日志
```

---

## 📦 数据模型

### 请求模型 (`TripPlanRequest`)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `destination` | `str` | 目的地城市 | `"北京"` |
| `start_date` | `str` | 开始日期 | `"2024-10-01"` |
| `end_date` | `str` | 结束日期 | `"2024-10-03"` |
| `preferences` | `List[str]` | 旅行偏好 | `["历史", "美食"]` |
| `hotel_preferences` | `List[str]` | 酒店偏好 | `["经济型"]` |
| `budget` | `str` | 预算水平 | `"经济"` / `"中等"` / `"豪华"` |

### 响应模型 (`TripPlanResponse`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 行程 ID |
| `trip_title` | `str` | 行程标题（AI 生成） |
| `total_budget` | `Budget` | 总预算（含门票/酒店/餐饮/交通拆分） |
| `days` | `List[DailyPlan]` | 每日行程详情 |
| `created_at` | `str` | 创建时间 |

### 单日行程 (`DailyPlan`)

每天包含：
- **景点** (`List[Attraction]`)：2~4 个景点，含名称、地址、经纬度、游览时长、门票价格等
- **酒店** (`List[Hotel]`)：1 家推荐酒店，含价格范围、评分、距离景点距离等
- **餐饮** (`List[Meal]`)：早/午/晚餐 + 可选特色小吃，含预估费用
- **预算** (`Budget`)：当日门票、酒店、餐饮、交通费用明细
- **主题** (`str`)：当日行程主题（如"古都文化探秘"）

---

## 🚀 快速开始

### 环境要求

- **Python** >= 3.11
- **uv**（推荐）或 pip 包管理器

### 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# LLM 配置（必填，以通义千问为例）
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL_NAME=qwen-plus-2025-12-01

# 高德地图 MCP（必填，用于景点/酒店/天气搜索）
AMAP_MCP_KEY=your_amap_key

# LangSmith 追踪（可选）
LANGSMITH_API_KEY=your_langsmith_key

# Langfuse 可观测性（可选）
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

> **获取 API Key：**
> - 通义千问：[阿里云 DashScope](https://dashscope.console.aliyun.com/)
> - 高德地图：[高德开放平台](https://lbs.amap.com/)

### 运行测试

```bash
python tests/test_planer.py
```

### 使用示例

```python
import asyncio
from backend.app.agents.multi_agnet import OrchestratorWorkerPlanner
from backend.app.models.trip import TripPlanRequest

async def plan_trip_example():
    # 创建规划器
    planner = OrchestratorWorkerPlanner()

    # 构建请求
    request = TripPlanRequest(
        destination="北京",
        start_date="2024-10-01",
        end_date="2024-10-03",
        preferences=["历史", "美食"],
        hotel_preferences=["经济型"],
        budget="中等",
    )

    # 执行规划
    response = await planner.plan_trip(request, user_id="user_001")
    print(response.model_dump_json(indent=2))

# 运行示例
if __name__ == "__main__":
    asyncio.run(plan_trip_example())
```

---

## 🔧 核心技术细节

### Token 超限问题解决

原有架构中，所有规划逻辑集中在一个 Agent 上一次性输出完整行程 JSON，7 天行程约需 11000+ token，容易超过模型输出上限。

**解决方案：分治 + 按天规划**

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| 单次 LLM 输出 | 整个行程（7天 ≈ 11000+ token） | 单天单维度（≈ 500~800 token） |
| 天数扩展性 | 5 天以上容易超限 | 无限制，逐天生成 |
| 错误隔离 | 一次失败全部失败 | 某天某 Agent 失败不影响其他天 |
| 预算准确性 | LLM 计算，容易出错 | 程序化计算，100% 准确 |

> 详细分析见 [`docs/token超限问题.md`](../docs/token超限问题.md)

### 地理位置验证

系统内置 **30 个热门旅游城市**的经纬度范围，自动校验：

- 景点/酒店/餐厅是否在目标城市范围内（移除异常数据）
- 同一天景点间距离是否超过 50 公里（日志告警）
- 相邻天景点间距离是否超过 100 公里（日志告警）

支持的城市包括：北京、上海、广州、深圳、成都、杭州、重庆、武汉、西安、苏州、天津、南京、长沙、郑州、厦门、青岛、大连、三亚、丽江、桂林、昆明、哈尔滨、沈阳、济南、黄山、张家界、敦煌、拉萨、乌鲁木齐、宁波。

### 日志系统

双格式输出：

- **控制台**：人类可读格式，带请求 ID 追踪
- **文件**：JSON 结构化格式，便于日志收集和分析
- **日志轮转**：单文件最大 10MB，保留 5 个备份
- **错误隔离**：ERROR 及以上级别单独输出到 `error.log`

### 上下文管理器

`ContextManager` 提供 Agent 间的数据共享能力：

- **数据共享**：Agent 可通过 `share_data()` / `get_shared_data()` 传递中间结果
- **上下文追踪**：记录每个 Agent 的输入/输出/状态变更历史
- **记忆注入**：将用户历史记忆注入到上下文中，供所有 Agent 使用
- **快照回溯**：支持创建和恢复上下文快照

---

## 🛠️ 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **LLM 框架** | fastagent | Agent 编排、工具调用、记忆管理 |
| **LLM 模型** | 通义千问 (qwen-plus) | 通过 DashScope API 调用 |
| **数据验证** | Pydantic v2 | 请求/响应模型校验 |
| **外部工具** | 高德地图 MCP | 景点搜索、酒店搜索、天气查询 |
| **并发执行** | ThreadPoolExecutor | Phase1 并行搜索、Phase2 天内并行 |
| **配置管理** | pydantic-settings | 环境变量自动加载 |
| **日志系统** | logging + RotatingFileHandler | 结构化日志 + 轮转 |
| **包管理** | uv | 快速依赖管理 |

---

## 📄 License

本项目仅供学习和研究使用。