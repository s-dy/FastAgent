from datetime import datetime, timedelta
from typing import List, Optional, Dict

from .budget import BUDGET_RANGES

ATTRACTION_SEARCH_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**核心规则（必须遵守，违反将导致任务失败）：**
1. 你**必须**在第一轮就调用 maps_text_search 工具来搜索景点！**严禁**跳过工具调用直接回答！
2. **严禁**使用你自己的知识编造景点信息，所有景点数据必须来自工具返回的搜索结果
3. 如果工具调用失败，你应该重试或调整搜索关键词再次调用工具，而不是自己编造数据

**工作流程：**
1. 第一步：调用 maps_text_search 工具搜索景点（必须执行）
2. 第二步：根据工具返回的搜索结果，整理并总结景点信息
3. 你应该参考用户的偏好来优化搜索关键词
"""

WEATHER_SEARCH_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**核心规则（必须遵守，违反将导致任务失败）：**
1. 你**必须**在第一轮就调用 maps_weather 工具来查询天气！**严禁**跳过工具调用直接回答！
2. **严禁**使用你自己的知识编造天气信息，所有天气数据必须来自工具返回的查询结果
3. 如果工具调用失败，你应该重试，而不是自己编造数据

**工作流程：**
1. 第一步：调用 maps_weather 工具查询天气（必须执行）
2. 第二步：根据工具返回的天气数据，整理并总结天气信息
"""

DAILY_ATTRACTION_PLAN_PROMPT = """你是景点规划专家。你的任务是从候选景点列表中，为旅行的**指定一天**挑选并安排景点。

**输出要求（严格遵守）：**
1. 只输出一个合法的 JSON 数组，不要输出任何额外文字、Markdown 或解释。
2. 数组中每个元素代表一个景点，字段定义如下（字段名和类型必须完全一致）：
   - name (string): 景点名称
   - address (string): 景点地址
   - location (object): 经纬度，包含 longitude (float) 和 latitude (float)
   - visit_duration (int): 建议游览时间，单位为**分钟**
   - description (string): 景点简介及游览建议，需体现时间安排（上午/下午/晚上）
   - category (string): 景点类别，如"历史文化"、"自然风光"等
   - rating (float): 评分，0~5
   - ticket_price (int): 门票价格，单位为元，免费则为 0

**规划约束：**
1. 每天安排 2~4 个景点
2. 所有景点必须在目标城市范围内
3. 同一天景点间距离不超过 50 公里，优先安排地理位置相近的景点
4. 按照合理的游览顺序排列（地理位置由近到远或形成环线）
"""

DAILY_HOTEL_PLAN_PROMPT = """你是酒店规划专家。你的任务是分析当天所有景点的地理分布，确定一个最佳住宿位置，然后搜索该位置附近的酒店并挑选最合适的一家。

**核心规则（必须遵守，违反将导致任务失败）：**
1. 你**必须**先分析景点位置，再调用工具搜索酒店！**严禁**跳过工具调用直接回答！
2. 酒店的名称、地址、位置信息必须来自工具返回的搜索结果，**严禁**编造不存在的酒店

**工作流程（严格按照以下步骤，不要多余操作）：**
1. 第一步（分析位置）：根据当天所有景点的经纬度，分析景点的地理分布，确定一个最佳住宿地点。选择策略：
   - 优先选择景点集中区域的中心位置附近的地标或商圈
   - 如果景点分散，优先靠近第二天首个景点或交通枢纽
   - 考虑周边餐饮、交通的便利性
2. 第二步（搜索酒店）：调用 search_hotels 工具，以确定的最佳住宿地点作为搜索关键词搜索酒店（必须执行），注意搜索关键词应该是"地点名"的格式，例如"王府井"、"西湖"
3. 第三步（挑选输出）：从搜索结果中挑选一家最合适的酒店，根据你的知识估算价格，立即输出 JSON 结果

**输出要求（严格遵守）：**
1. 搜索完成后，只输出一个合法的 JSON 对象（单个酒店），不要输出数组，不要输出任何额外文字。
2. 字段定义如下（字段名和类型必须完全一致）：
   - name (string): 酒店名称（必须来自搜索结果）
   - address (string): 酒店地址（必须来自搜索结果）
   - location (object|null): 经纬度，包含 longitude (float) 和 latitude (float)，没有则为 null
   - price_range (string): 价格范围，如"300-500元/晚"（根据你的知识估算）
   - rating (string): 评分
   - distance (string): 距离当天主要景点的距离，如"1.2公里"
   - type (string): 酒店类型，如"经济型"、"中档型"、"豪华型"等
   - estimated_cost (int): 预估费用，单位为元/晚（根据你的知识估算，必须符合用户预算）

**规划约束：**
1. 只搜索一次，只推荐一家酒店
2. 优先推荐位于景点集中区域中心位置的酒店
3. 符合用户的预算水平和酒店偏好
4. 不同天可以推荐同一家酒店（如果位置合理）
"""

DAILY_DINING_PLAN_PROMPT = """你是餐饮规划专家。你的任务是为旅行的**指定一天**推荐合适的餐饮。

**重要提示（关于工具使用）：**
- 你可以使用 maps_text_search 搜索景点附近的餐厅，获取真实的餐厅名称和地址
- 高德地图 API **不会返回餐厅价格信息**，**不要**反复调用工具试图获取价格
- 搜索到餐厅后，请根据你的知识**自行估算** estimated_cost
- 你只需要调用 1 次 maps_text_search 搜索餐厅即可，然后立即输出 JSON 结果

**输出要求（严格遵守）：**
1. 只输出一个合法的 JSON 数组，不要输出任何额外文字。
2. 数组中每个元素代表一顿餐饮，字段定义如下（字段名和类型必须完全一致）：
   - type (string): 餐饮类型，必须为 "breakfast"、"lunch"、"dinner" 或 "snack" 之一
   - name (string): 餐厅名称或推荐菜品
   - address (string|null): 餐厅地址，没有则为 null
   - location (object|null): 经纬度，包含 longitude (float) 和 latitude (float)，没有则为 null
   - description (string|null): 推荐理由或特色菜品描述
   - estimated_cost (int): 预估人均费用，单位为元（根据你的知识估算，必须符合用户预算）

**规划约束：**
1. 每天至少安排早餐、午餐、晚餐各一顿
2. 可以额外推荐 1~2 个特色小吃（type 为 "snack"）
3. 餐厅位置应靠近当天的景点
4. 不要在多天中重复推荐同一家餐厅
5. 符合用户的预算水平
"""

DAILY_THEME_PROMPT = """你是旅行文案专家。根据以下行程信息，为整个旅行生成一个吸引人的标题，并为每一天生成一个主题。

**输出要求（严格遵守）：**
只输出一个合法的 JSON 对象，不要输出任何额外文字。格式如下：
{
  "trip_title": "整个旅行的标题",
  "daily_themes": ["第1天主题", "第2天主题", ...]
}

**要求：**
1. trip_title 要吸引人，能体现目的地和行程特色
2. 每天的主题要简洁（10字以内），体现该天的主要活动特色
"""

def get_weather_for_date(raw_weather: List[Dict], target_date: str) -> Optional[Dict]:
    """根据日期从天气列表中匹配当天的天气数据"""
    for weather_item in raw_weather:
        if weather_item.get("date") == target_date:
            return weather_item
    return None

def format_weather_to_text(weather_data: Optional[Dict]) -> str:
    """将天气字典转为可读的 prompt 文本"""
    if not weather_data:
        return "天气数据暂不可用"

    day_weather = weather_data.get("dayweather", "未知")
    night_weather = weather_data.get("nightweather", "未知")
    day_temp = weather_data.get("daytemp", "?")
    night_temp = weather_data.get("nighttemp", "?")
    day_wind = weather_data.get("daywind", "未知")
    day_power = weather_data.get("daypower", "未知")

    weather_text = f"白天{day_weather}，夜间{night_weather}，气温{night_temp}~{day_temp}°C，{day_wind}风{day_power}级"

    if any(keyword in day_weather for keyword in ["雨", "雪", "暴"]):
        weather_text += "（建议安排室内景点）"
    elif any(keyword in day_weather for keyword in ["阴", "多云"]):
        weather_text += "（适合户外活动）"
    elif "晴" in day_weather:
        weather_text += "（天气晴好，适合户外游览）"

    return weather_text

def calculate_current_date(start_date: str, current_day: int) -> str:
    """根据出发日期和当前天数计算当天的日期字符串"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    current_dt = start_dt + timedelta(days=current_day - 1)
    return current_dt.strftime("%Y-%m-%d")

def format_attraction_detail(attraction: Dict) -> str:
    """将单个景点数据转为可读的 prompt 文本行"""
    name = attraction.get("name", "未知景点")
    address = attraction.get("address", "")
    detail_raw = attraction.get("detail", "")

    parts = [f"- **{name}**"]
    if address:
        parts.append(f"地址: {address}")

    if detail_raw and not detail_raw.startswith("工具执行失败"):
        try:
            import ast
            detail = ast.literal_eval(detail_raw) if isinstance(detail_raw, str) else detail_raw
            location = detail.get("location", "")
            if location:
                parts.append(f"坐标: {location}")
            rating = detail.get("rating", "")
            if rating:
                parts.append(f"评分: {rating}")
            level = detail.get("level", "")
            if level:
                parts.append(f"等级: {level}")
            opentime = detail.get("opentime2", "")
            if opentime:
                parts.append(f"开放时间: {opentime}")
        except (ValueError, SyntaxError):
            pass

    return " | ".join(parts)

def format_attractions_to_prompt(raw_attractions: List[Dict]) -> str:
    """将景点列表转为 LLM 可读的 prompt 文本"""
    if not raw_attractions:
        return "暂无候选景点数据"

    lines = []
    for idx, attraction in enumerate(raw_attractions, 1):
        lines.append(f"{idx}. {format_attraction_detail(attraction)}")
    return "\n".join(lines)

def filter_unassigned_attractions(raw_attractions: List[Dict], assigned_names: List[str]) -> List[Dict]:
    """从候选景点列表中过滤掉已分配到其他天的景点"""
    if not assigned_names:
        return raw_attractions
    assigned_set = set(assigned_names)
    return [a for a in raw_attractions if a.get("name", "") not in assigned_set]

def build_daily_attraction_prompt(
    day_num: int,
    destination: str,
    raw_attractions: List[Dict],
    weather_text: str,
    preferences: List[str],
    budget_level: str = "中等",
    memory_context: str = "",
) -> str:
    """构建单日景点规划的 prompt（传入的 raw_attractions 应已过滤掉已分配景点）"""
    pref_str = "、".join(preferences) if preferences else "无特殊偏好"
    budget_info = BUDGET_RANGES.get(budget_level, BUDGET_RANGES["中等"])
    attractions_text = format_attractions_to_prompt(raw_attractions)
    prompt = (
        f"请为前往 {destination} 旅行的第 {day_num} 天规划景点。\n\n"
        f"**用户偏好：** {pref_str}\n"
        f"**预算水平：** {budget_level}（{budget_info['description']}）\n"
        f"**每日总预算上限：** {budget_info['daily_total_max']}元/天\n"
        f"**当天天气：** {weather_text}\n\n"
        f"**候选景点列表（从以下景点中挑选，所有景点均可选择）：**\n{attractions_text}\n\n"
        f"**注意：** 候选景点数据来自高德地图，不包含门票价格信息。请根据你的知识估算每个景点的门票价格（estimated_cost），"
        f"免费景点请填写0。\n"
        f"请严格按照系统提示中的 JSON 格式输出。"
    )
    if memory_context:
        prompt += f"\n\n## 用户历史偏好参考\n{memory_context}"
    return prompt

def build_daily_hotel_prompt(
    start_date: str,
    day_num: int,
    destination: str,
    day_attractions_summary: str,
    budget_level: str,
    hotel_preferences: List[str],
    memory_context: str = "",
) -> str:
    """构建单日酒店规划的 prompt"""
    hotel_pref_str = "、".join(hotel_preferences) if hotel_preferences else "无特殊偏好"
    budget_info = BUDGET_RANGES.get(budget_level, BUDGET_RANGES["中等"])
    prompt = (
        f"请为前往 {destination} 旅行的第 {day_num} 天搜索并推荐酒店。\n\n"
        f"**入住日期：** {start_date}\n"
        f"**预算水平：** {budget_level}（{budget_info['description']}）\n"
        f"**酒店价格范围：** {budget_info['hotel_range']}\n"
        f"**酒店价格上限：** {budget_info['hotel_max']}元/晚\n"
        f"**酒店偏好：** {hotel_pref_str}\n"
        f"**当天景点位置参考：** {day_attractions_summary}\n\n"
        f"请根据以上景点位置，搜索附近的酒店，然后从搜索结果中挑选价格在 {budget_info['hotel_range']} 范围内最合适的一家。\n"
        f"**重要：推荐的酒店 estimated_cost 必须不超过 {budget_info['hotel_max']} 元/晚。**\n"
        f"搜索完成后，请严格按照系统提示中的 JSON 格式输出。"
    )
    if memory_context:
        prompt += f"\n\n## 用户历史偏好参考\n{memory_context}"
    return prompt

def build_daily_dining_prompt(
    day_num: int,
    destination: str,
    day_attractions_summary: str,
    budget_level: str,
    assigned_dining_names: List[str],
    memory_context: str = "",
) -> str:
    """构建单日餐饮规划的 prompt"""
    assigned_str = "、".join(assigned_dining_names) if assigned_dining_names else "无"
    budget_info = BUDGET_RANGES.get(budget_level, BUDGET_RANGES["中等"])
    prompt = (
        f"请为前往 {destination} 旅行的第 {day_num} 天推荐餐饮。\n\n"
        f"**目的地：** {destination}\n"
        f"**预算水平：** {budget_level}（{budget_info['description']}）\n"
        f"**餐饮人均价格范围：** {budget_info['dining_per_meal']}\n"
        f"**单餐人均上限：** {budget_info['dining_meal_max']}元/人\n"
        f"**当天景点位置参考：** {day_attractions_summary}\n"
        f"**已在其他天推荐过的餐厅（不要重复）：** {assigned_str}\n\n"
        f"**重要：每顿餐饮的 estimated_cost 必须在 {budget_info['dining_per_meal']} 范围内。**\n"
        f"请严格按照系统提示中的 JSON 格式输出。"
    )
    if memory_context:
        prompt += f"\n\n## 用户历史偏好参考\n{memory_context}"
    return prompt

def build_theme_prompt(destination: str, duration: int, daily_summaries: List[str]) -> str:
    """构建行程标题与主题生成的 prompt"""
    summaries_text = ""
    for idx, summary in enumerate(daily_summaries, 1):
        summaries_text += f"第{idx}天：{summary}\n"
    return (
        f"请为前往 {destination} 的 {duration} 天旅行生成标题和每天主题。\n\n"
        f"**每天行程概要：**\n{summaries_text}\n"
        f"请严格按照系统提示中的 JSON 格式输出。"
    )
