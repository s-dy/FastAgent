## HotelMCP

基于 [FastMCP](https://github.com/jlowin/fastmcp) 构建的酒店搜索 MCP 服务，通过 Booking.com 数据源提供酒店搜索能力，可供 AI Agent 调用。

### 数据来源
- https://www.booking.com/

### 功能

- **酒店搜索**：根据关键词（地点、酒店名称）搜索酒店，返回酒店名称、评分、星级、价格、房型等详细信息
- **MCP 协议**：以 HTTP 方式暴露标准 MCP Tool，可直接接入支持 MCP 协议的 AI 客户端

### 环境要求

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) 包管理器

### 本地运行

```bash
# 安装依赖
uv sync

# 启动服务（HTTP 模式，端口 8000）
uv run python server.py
```

### Docker 部署

```bash
# 构建镜像
docker build -t hotel-mcp .

# 运行容器
docker run -d -p 8000:8000 --name hotel-mcp hotel-mcp
```

### MCP Tool 说明

#### `search_hotels`

根据关键词搜索酒店详情。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prefix_query` | str | 是 | - | 搜索关键词（地点、酒店名称） |
| `checkin` | str | 是 | - | 入住日期，格式：`2026-01-01` |
| `checkout` | str | 是 | - | 退房日期，格式：`2026-01-02` |
| `nb_adults` | int | 否 | 2 | 成人数量 |
| `nb_children` | int | 否 | 0 | 儿童数量 |
| `nb_rooms` | int | 否 | 1 | 房间数量 |
| `offset` | int | 否 | 25 | 分页参数，从 25 开始，步长 25 |

**返回示例：**

```json
[
  {
    "id": "12345",
    "name": "北京某酒店",
    "score": 8.5,
    "starRating": 4,
    "price": "500",
    "room": "大床房、双床房",
    "location": { "city": "北京", "displayLocation": "朝阳区" },
    "isClosed": false,
    "isSoldOut": false
  }
]
```
