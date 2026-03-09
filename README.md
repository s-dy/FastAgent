# 智能旅行规划系统

基于多智能体协作的 AI 旅行规划助手，输入目的地和日期即可自动生成包含景点、酒店、餐饮、天气的完整行程方案。

## 📝 项目简介

智能旅行规划系统是一个结合大语言模型（LLM）、向量数据库和地图服务的全栈旅游规划应用。系统通过 6 个专业化智能体协作，经过三阶段流水线（并行搜索 → 按天规划 → 验证拼装），为用户提供从景点搜索、酒店推荐、天气查询到完整行程生成的端到端服务。

## ✨ 核心功能

- **智能行程规划**：输入目的地、日期、偏好，AI 自动生成完整行程，支持 30+ 热门旅游城市
- **多智能体协作**：景点搜索、天气查询、酒店推荐、餐饮规划、主题生成等 6 个专业 Agent 分工协作
- **地图可视化**：高德地图集成，标注景点、餐厅、酒店位置
- **预算计算**：自动统计门票、酒店、餐饮、交通四类费用
- **实时天气**：通过高德 MCP 工具查询行程期间天气预报，雨天自动优先室内景点
- **地理位置验证**：确保景点在目标城市范围内，同一天景点距离控制在 50km 内
- **用户认证**：JWT 令牌认证 + 访客模式，支持注册登录和行程管理
- **向量记忆**：Milvus 向量数据库记录用户偏好和历史行程，越用越智能
- **行程编辑**：支持拖拽排序景点、添加/删除景点和餐厅、个人备注
- **导出功能**：支持导出为 PDF 或图片格式
- **并行优化**：Phase1 景点和天气并行搜索，Phase2 每天三个 Agent 并行规划
- **企业级特性**：请求限流、熔断降级、结构化日志、统一异常处理

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + TypeScript)              │
│  Home → LoadingProgress → Result / EditPlan / MyTrips    │
│  MapView · BudgetSummary · ExportButtons · UserInfo      │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / REST API
┌──────────────────────────▼──────────────────────────────┐
│              后端 (FastAPI + Uvicorn)                     │
│                                                          │
│  中间件链: RequestID → Auth → RateLimit → CORS           │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │     OrchestratorWorkerPlanner (协调器-工作器)      │     │
│  │                                                   │     │
│  │  基于 LangGraph 的 Send API 实现动态任务调度        │     │
│  │                                                   │     │
│  │  ┌─────────────────────────────────────────┐     │     │
│  │  │  Orchestrator (协调器)                  │     │     │
│  │  │  - 任务分解与委派                        │     │     │
│  │  │  - 动态生成 TripSection                 │     │     │
│  │  │  - 管理任务依赖关系                      │     │     │
│  │  └──────────────┬──────────────────────────┘     │     │
│  │                 │ Send API (动态节点创建)          │     │
│  │                 ▼                                 │     │
│  │  ┌─────────────────────────────────────────┐     │     │
│  │  │  Workers (工作节点，并行执行)            │     │     │
│  │  │                                         │     │     │
│  │  │  景点搜索 Worker                        │     │     │
│  │  │  天气查询 Worker                        │     │     │
│  │  │  每日规划 Worker (多个实例，每天一个)    │     │     │
│  │  └──────────────┬──────────────────────────┘     │     │
│  │                 │                                 │     │
│  │                 ▼                                 │     │
│  │  ┌─────────────────────────────────────────┐     │     │
│  │  │  Synthesizer (合成器)                   │     │     │
│  │  │  - 汇总所有工作节点结果                  │     │     │
│  │  │  - 生成标题和主题                        │     │     │
│  │  │  - 计算总预算                           │     │     │
│  │  │  - 验证相邻天行程                        │     │     │
│  │  └─────────────────────────────────────────┘     │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  外部服务:                                                │
│    ├─ 高德地图 MCP (景点/酒店/天气搜索工具)               │
│    ├─ 通义千问 LLM (qwen-plus)                           │
│    ├─ Redis (用户数据 + 行程持久化)                       │
│    └─ Milvus (向量记忆存储)                               │
└──────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

### 后端
| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| LLM 服务 | 通义千问 (qwen-plus) / OpenAI 兼容接口 |
| Agent 框架 | HelloAgents |
| 向量数据库 | Milvus + Sentence-Transformers |
| 数据持久化 | Redis |
| 地图服务 | 高德地图 API（MCP 协议） |
| 认证 | JWT (PyJWT) + Bcrypt |
| 数据验证 | Pydantic v2 |

### 前端
| 类别 | 技术 |
|------|------|
| 框架 | Vue 3 + TypeScript |
| 构建工具 | Vite |
| UI 组件库 | Element Plus |
| 路由 | Vue Router 4 |
| 状态管理 | Pinia |
| 地图 | 高德地图 JS API |
| 导出 | html2canvas + jsPDF |
| CSS | Sass + Tailwind CSS |

## 📁 项目结构

```
TravelAgent/
├── backend/                          # 后端服务
│   ├── run.py                        # 启动入口
│   ├── pyproject.toml                # Python 依赖
│   ├── app/
│   │   ├── main.py                   # FastAPI 应用 + 中间件注册
│   │   ├── config.py                 # 配置管理 (环境变量)
│   │   ├── agents/                   # 智能体
│   │   │   ├── multi_agnet.py          # 协调器-工作器架构（Orchestrator-Worker）
│   │   │   ├── agents.py               # Agent 定义和工具
│   │   │   ├── enhanced_agent.py       # Agent 基类（工具调用/JSON解析）
│   │   │   └── planner.py              # 旧版规划器（已废弃）
│   │   ├── api/v1/                   # REST API
│   │   │   ├── trip.py               # 行程规划接口
│   │   │   └── auth.py               # 用户认证接口
│   │   ├── middleware/               # 中间件
│   │   │   ├── request_id.py         # 请求 ID 追踪
│   │   │   ├── auth.py               # JWT 认证 + 访客模式
│   │   │   ├── rate_limit.py         # 滑动窗口限流
│   │   │   ├── circuit_breaker.py    # 熔断器
│   │   │   └── degradation.py        # 降级策略
│   │   ├── exceptions/               # 异常处理
│   │   │   ├── error_codes.py        # 统一错误码
│   │   │   ├── custom_exceptions.py  # 业务异常类
│   │   │   └── exception_handler.py  # 全局异常处理器
│   │   ├── models/                   # Pydantic 数据模型
│   │   │   ├── common.py             # 景点/酒店/餐饮/天气/预算
│   │   │   └── trip.py               # 行程请求/响应
│   │   ├── services/                 # 服务层
│   │   │   ├── redis_service.py      # Redis 用户和行程 CRUD
│   │   │   └── context_manager.py    # Agent 间上下文共享
│   │   └── observability/            # 可观测性
│   │       └── logger.py             # 结构化日志 (JSON + 请求ID)
│   └── tests/                        # 测试
│
├── frontend/                         # 前端应用
│   ├── package.json                  # Node 依赖
│   ├── vite.config.ts                # Vite 配置
│   ├── src/
│   │   ├── main.ts                   # 应用入口
│   │   ├── App.vue                   # 根组件 (导航栏 + 路由视图)
│   │   ├── router/index.ts           # 路由配置 (6 个页面)
│   │   ├── stores/auth.ts            # Pinia 认证状态管理
│   │   ├── services/api.ts           # Axios API 封装
│   │   ├── types/index.ts            # TypeScript 类型定义
│   │   ├── utils/tripDataAdapter.ts  # 后端→前端数据适配
│   │   ├── views/                    # 页面组件
│   │   │   ├── Home.vue              # 首页 (行程规划表单)
│   │   │   ├── Result.vue            # 行程详情展示
│   │   │   ├── EditPlan.vue          # 行程编辑 (拖拽排序)
│   │   │   ├── MyTrips.vue           # 我的行程列表
│   │   │   ├── Login.vue             # 登录/注册
│   │   │   └── Profile.vue           # 个人资料
│   │   └── components/               # 公共组件
│   │       ├── MapView.vue           # 高德地图视图
│   │       ├── BudgetSummary.vue     # 预算明细
│   │       ├── ExportButtons.vue     # PDF/图片导出
│   │       ├── LoadingProgress.vue   # 规划进度条
│   │       └── UserInfo.vue          # 用户信息展示
│   └── public/
│
└── README.md
```

## 🤖 智能体设计

系统采用**协调器-工作器（Orchestrator-Worker）架构**，基于 LangGraph 的 Send API 实现多智能体协作：

| 组件 | 角色 | 工具调用 | 说明 |
|-------|------|:--------:|------|
| **Orchestrator** | 任务协调器 | ❌ | 分解任务、生成 TripSection、动态分配工作节点 |
| **AttractionSearchWorker** | 景点搜索工作节点 | ✅ | 通过高德 MCP 搜索目的地景点 |
| **WeatherSearchWorker** | 天气查询工作节点 | ✅ | 查询行程期间每日天气预报 |
| **DailyPlanningWorker** | 每日规划工作节点 | ✅ | 规划单日行程（景点、酒店、餐饮） |
| **Synthesizer** | 结果合成器 | ❌ | 汇总结果、生成标题主题、计算预算 |

### 协调器-工作器执行流程

```
阶段 1: 数据收集（并行）
  ├─ Orchestrator 生成景点搜索和天气查询任务
  ├─ Send API 创建 AttractionSearchWorker 和 WeatherSearchWorker
  └─ Workers 并行执行，结果写入共享状态

阶段 2: 每日规划（并行）
  ├─ Orchestrator 检测到阶段1完成
  ├─ 将景点均匀分配到每一天
  ├─ Send API 创建 N 个 DailyPlanningWorker（N = 行程天数）
  └─ Workers 并行执行每日规划，结果写入共享状态

阶段 3: 结果合成
  ├─ Synthesizer 汇总所有工作节点结果
  ├─ 生成行程标题和每日主题
  ├─ 计算总预算并验证相邻天行程
  └─ 返回最终行程计划
```

### 核心特性

- **动态任务调度**：Orchestrator 根据执行进度动态生成任务
- **并行执行**：所有工作节点并行运行，大幅提升效率
- **状态共享**：通过 `operator.add` reducer 实现安全的状态聚合
- **任务依赖管理**：通过条件边自动管理任务间的依赖关系

## 🔌 API 接口

### 行程规划

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/trips/plan` | 创建行程规划 |
| GET | `/api/v1/trips/list` | 获取用户行程列表 |
| GET | `/api/v1/trips/{trip_id}` | 获取行程详情 |
| DELETE | `/api/v1/trips/{trip_id}` | 删除行程 |

### 用户认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |
| PUT | `/api/v1/auth/me` | 更新用户资料 |
| POST | `/api/v1/auth/change-password` | 修改密码 |
| POST | `/api/v1/auth/logout` | 退出登录 |
| POST | `/api/v1/auth/upload-avatar` | 上传头像 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康检查 |

## 🚀 快速开始

### 环境要求

- **Python** 3.11+
- **Node.js** 16+
- **Redis** 6+
- **Milvus** 2.x（可选，用于向量记忆）
- **高德地图 API Key**
- **通义千问 API Key**（或其他 OpenAI 兼容 LLM）

### 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt
# 或使用 uv
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key 等配置

# 启动服务
python run.py
```

后端默认运行在 `http://localhost:8000`，API 文档访问 `http://localhost:8000/docs`。

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

前端默认运行在 `http://localhost:5173`。

### 环境变量配置

在 `backend/.env` 中配置以下变量：

```env
# LLM 服务
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_MODEL_NAME=qwen-plus
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT 认证
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRY_HOURS=24

# Milvus 向量数据库 (可选)
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 服务配置
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
```

## 🌍 支持的城市

系统内置了 30+ 热门旅游城市的地理边界数据，用于景点位置验证：

北京、上海、广州、深圳、成都、杭州、重庆、武汉、西安、苏州、天津、南京、长沙、郑州、厦门、青岛、大连、三亚、丽江、桂林、昆明、哈尔滨、沈阳、济南、黄山、张家界、敦煌、拉萨、乌鲁木齐、宁波 等。

## 🔮 未来计划

- [ ] 交通规划 Agent：自动规划景点间的交通方式和路线
- [ ] 社交功能：支持行程分享、评论、收藏
- [ ] 多语言支持：国际化界面
- [ ] 移动端：小程序或 APP
- [ ] 实时协作：多人共同编辑行程
- [ ] 预算预测：基于历史数据预测实际花费