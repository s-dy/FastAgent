# 智能旅行规划系统

基于 AI 的智能旅行规划助手，自动为您生成个性化旅行方案。

## 📝 项目简介

智能旅行规划系统是一个结合大语言模型（LLM）、向量数据库和地图服务的全栈旅游规划应用。它通过多智能体协作，为用户提供从景点搜索、酒店推荐、天气查询到完整行程生成的端到端服务。

### 解决的问题
- **繁琐的行程规划**：传统规划需要查阅大量攻略、地图和多个服务
- **个性化不足**：通用攻略无法满足个人偏好和特殊需求
- **信息分散**：景点、酒店、交通、天气等信息需要从不同渠道获取
- **缺乏记忆**：无法记住用户的旅行历史和偏好，每次都需要重新输入

### 适用场景
- 个人旅行规划：快速生成个性化行程
- 家庭出游：根据家庭成员偏好推荐合适行程
- 商务旅行：高效安排出差行程
- 深度游：基于历史记忆的渐进式探索

## ✨ 核心功能

- [ ] **智能行程规划**：输入目的地、日期、偏好，AI 自动生成完整行程，目前支持30个热门旅游城市的相关精确规划
- [ ] **地图可视化**：高德地图集成，标注景点位置和游览路线
- [ ] **预算计算**：自动统计门票、酒店、餐饮、交通费用
- [ ] **用户认证**：支持注册登录和行程记录
- [ ] **记忆学习**：向量数据库记录用户偏好，越用越智能
- [ ] **实时天气**：查询行程期间天气预报
- [ ] **行程编辑**：支持添加、删除、调整景点和活动
- [ ] **导出功能**：支持导出为 PDF 或图片格式
- [ ] **多智能体协作**：专业化 Agent 分工协作
- [ ] **地理位置验证**：确保景点位置准确性
- [ ] **性能优化**：并行查询提升响应速度
- [ ] **限流熔断**：API 请求限流和熔断保护

## 🛠️ 技术栈

### 后端
- **框架**：FastAPI
- **LLM 服务**：OpenAI API / 智谱 AI / 通义千问
- **Agent 框架**：HelloAgents
- **向量数据库**：FAISS + Sentence-Transformers
- **缓存数据库**：Redis
- **地图服务**：高德地图 API（MCP 协议）
- **图片服务**：Unsplash API
- **认证**：JWT + Bcrypt

### 前端
- **框架**：Vue 3 + TypeScript
- **构建工具**：Vite
- **组件库**：Element Plus
- **路由**：Vue Router
- **状态管理**：Pinia
- **地图**：高德地图 JS API
- **导出**：html2canvas + jsPDF

## 🎯 项目亮点

- **多智能体协作**：景点搜索专家、酒店推荐专家、天气查询专家、行程规划专家协同工作
- **向量记忆系统**：基于 FAISS 的向量数据库，记录用户偏好和历史行程，越用越智能
- **地理位置验证**：确保所有景点都在目标城市范围内，同一天景点距离控制在 50 公里内
- **并行性能优化**：景点、酒店、天气查询并行执行，响应时间从 8-13 秒优化到 3-5 秒
- **企业级架构**：包含中间件、异常处理、日志系统、限流熔断等完整的企业级特性

## 🔮 未来计划

- [ ] 智能体增强：增加餐厅推荐、交通规划等专业化 Agent
- [ ] 社交功能：支持行程分享、评论、收藏
- [ ] 多语言支持：国际化支持多语言界面
- [ ] 移动端优化：开发小程序或 APP
- [ ] 实时协作：支持多人共同编辑行程
- [ ] 预算智能：基于历史数据预测实际花费

---

## 🚀 快速开始

### 运行环境
**后端**：Python 3.11、pip、Redis
**前端**：Node.js 16+、npm
**外部服务**：高德地图 API Key、Unsplash API Key、LLM API Key

### 安装步骤
前期工作：
你需要准备以下 API 密钥：

LLM 的 API(OpenAI、DeepSeek 等)
高德地图 Web 服务 Key：访问 https://console.amap.com/ 注册并创建应用
Unsplash Access Key：访问 https://unsplash.com/developers 注册并创建应用
将所有 API 密钥放入.env文件。
1. **克隆项目**
```bash
git clone <repository-url>
cd trip_planner
```

2. **后端配置**

**安装并启动 Redis**：
- **Windows**：下载并安装 Redis for Windows，在redis安装目录下使用命令：redis-server.exe
- **macOS**：`brew install redis && brew services start redis`
- **Linux**：`sudo apt-get install redis-server && sudo systemctl start redis`

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件，填入必要配置：
#   - LLM_API_KEY（必需）：LLM API 密钥
#   - AMAP_API_KEY（必需）：高德地图 API 密钥
#   - UNSPLASH_ACCESS_KEY（必需）：Unsplash API 密钥
#   - REDIS_HOST、REDIS_PORT（默认 localhost:6379）：Redis 连接信息
python run.py
```
后端服务将在 http://localhost:8000 启动

3. **前端配置**
```bash
cd ../frontend
npm install
# 创建 .env文件，配置后端地址和高德地图 Key
cp .env.example .env
npm run dev
```
前端服务将在 http://localhost:5173 启动

### 访问应用
打开浏览器访问 http://localhost:5173，输入目的地、日期、偏好等信息，点击"生成行程"即可使用。

---

## 📁 项目结构

```
trip_planner/
├── backend/          # 后端服务（FastAPI）
│   ├── app/
│   │   ├── agents/     # 智能体实现
│   │   ├── api/        # API 路由
│   │   ├── middleware/  # 中间件
│   │   ├── services/    # 业务服务
│   │   └── tools/      # MCP 工具
│   └── run.py          # 启动入口
├── frontend/         # 前端应用（Vue 3）
│   └── src/
│       ├── components/  # Vue 组件
│       ├── views/      # 页面视图
│       └── services/   # API 服务
└── README.md         # 项目文档
```