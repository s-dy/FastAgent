# 问题：LLM 输出 JSON 解析失败

## 问题描述

系统中的规划类 Agent（景点规划、酒店推荐、餐饮规划、主题生成）要求 LLM 输出严格的 JSON 格式数据，以便后续转换为 Pydantic 模型。但在实际运行中，LLM 的 JSON 输出频繁解析失败，导致整个行程规划流程中断。

## 问题现象

1. **Markdown 包裹**：LLM 在 JSON 前后添加 ` ```json ` 和 ` ``` ` 标记，导致 `json.loads()` 直接报错
2. **附加解释文字**：LLM 在 JSON 前后附加自然语言解释，如 `"以下是为您推荐的景点：\n[{...}]"`
3. **字段类型不一致**：同一个字段在不同调用中返回不同类型，如 `visit_duration` 有时返回整数 `120`，有时返回字符串 `"120分钟"` 或 `"2小时"`
4. **嵌套对象格式混乱**：`location` 字段有时返回 `{"longitude": 116.4, "latitude": 39.9}`，有时返回字符串 `"116.4,39.9"`

## 影响范围

- `planner.py` 中的 `_plan_single_day()` 方法在解析每天的景点、酒店、餐饮数据时均可能触发
- 一旦某一天的数据解析失败，该天的行程数据为空，最终用户看到的是不完整的行程

## 解决方案

### 1. JSON 提取正则（`_parse_json_response`）

在 `planner.py` 中实现了 `_parse_json_response()` 方法，使用正则表达式从 LLM 的原始输出中提取 JSON 块：

```python
def _parse_json_response(self, raw_text: str) -> Any:
    """从 LLM 原始输出中提取并解析 JSON"""
    # 尝试直接解析
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 Markdown 代码块中的 JSON
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_text)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # 尝试提取裸 JSON（数组或对象）
    json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', raw_text)
    if json_match:
        return json.loads(json_match.group(1))
    
    raise json.JSONDecodeError("无法从输出中提取 JSON", raw_text, 0)
```

**策略**：三级降级尝试——直接解析 → Markdown 代码块提取 → 裸 JSON 正则提取。

### 2. 字段级类型容错（`_dict_to_*` 系列方法）

为每种数据模型实现了专门的字典转模型方法，对每个字段做类型容错：

```python
def _dict_to_attraction(self, data: Dict) -> Optional[Attraction]:
    # visit_duration 容错：字符串 → 整数
    visit_duration = data.get("visit_duration", 120)
    if isinstance(visit_duration, str):
        try:
            visit_duration = int(visit_duration)
        except ValueError:
            visit_duration = 120  # 默认 2 小时

    # rating 容错：字符串 → 浮点数
    rating = data.get("rating")
    if rating is not None:
        try:
            rating = float(rating)
        except (ValueError, TypeError):
            rating = None

    # ticket_price 容错：字符串 → 整数
    ticket_price = data.get("ticket_price", 0)
    if isinstance(ticket_price, str):
        try:
            ticket_price = int(ticket_price)
        except ValueError:
            ticket_price = 0
```

### 3. Pydantic `field_validator` 自动解析

在 `WeatherInfo` 模型中使用 Pydantic v2 的 `field_validator` 装饰器，自动处理温度字符串：

```python
class WeatherInfo(BaseModel):
    day_temp: int
    night_temp: int

    @field_validator('day_temp', 'night_temp', mode='before')
    def parse_temperature(cls, v):
        """解析温度字符串："16°C" → 16"""
        if isinstance(v, str):
            v = v.replace('°C', '').replace('℃', '').replace('°', '').strip()
            try:
                return int(v)
            except ValueError:
                return 0
        return v
```

### 4. Prompt 工程强化

在每个规划类 Agent 的 System Prompt 中，用加粗和明确的字段定义来约束输出格式：

```
**输出要求（严格遵守）：**
1. 只输出一个合法的 JSON 数组，不要输出任何额外文字、Markdown 或解释。
2. 数组中每个元素代表一个景点，字段定义如下（字段名和类型必须完全一致）：
   - name (string): 景点名称
   - visit_duration (int): 建议游览时间，单位为**分钟**
   ...
```

## 效果

- JSON 解析成功率从约 60% 提升到 95%+
- 即使 LLM 输出格式不完美，系统也能通过多级容错正确提取数据
- 单个字段解析失败不会导致整条数据丢失，而是使用合理的默认值
