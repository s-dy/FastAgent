from typing import Optional
from fastagent.core import LLMClient
from fastagent.tools import ToolRegistry
from fastagent.memory import MemoryConfig, MemoryManager
from app.agents.enhanced_agent import EnhancedAgent
from app.services.context_manager import ContextManager


# ============================================================
# Phase1: 搜索类 Agent 提示词
# ============================================================

ATTRACTION_SEARCH_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**重要提示:**
1. 你必须使用工具来搜索景点!不要自己编造景点信息!
2. 你应该参考用户的历史偏好和相似行程来优化搜索策略
3. 如果从上下文信息中了解到用户喜欢特定类型的景点，优先搜索这些类型
4. 搜索完成后，总结信息
"""

WEATHER_SEARCH_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
1. 你必须使用工具来查询天气!不要自己编造天气信息!
2. 你应该查询整个行程期间的天气，而不仅仅是当前日期
3. 搜索完成后，总结信息
"""
# ============================================================
# Phase2: 按天规划类 Agent 提示词
# 字段名严格对齐 app/models/common.py 中的 Pydantic 模型
# ============================================================

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
   - image_url (string|null): 景点图片URL，没有则为 null
   - ticket_price (int): 门票价格，单位为元，免费则为 0

**规划约束：**
1. 每天安排 2~4 个景点
2. 所有景点必须在目标城市范围内
3. 同一天景点间距离不超过 50 公里，优先安排地理位置相近的景点
4. 不要推荐已在其他天分配过的景点
5. 考虑当天天气情况，雨天优先安排室内景点
6. 按照合理的游览顺序排列（地理位置由近到远或形成环线）
"""

DAILY_HOTEL_PLAN_PROMPT = """你是酒店规划专家。你的任务是根据当天景点的位置，**使用工具动态搜索**附近的酒店，然后从搜索结果中挑选最合适的一家。

**工作流程：**
1. 根据提供的当天景点位置信息，使用工具搜索景点附近的酒店
2. 从搜索结果中挑选最符合用户需求的一家酒店
3. 按照下面的 JSON 格式输出结果

**重要提示：**
1. 你必须使用工具来搜索酒店！不要自己编造酒店信息！
2. 搜索时应以当天景点的中心位置为基准，搜索附近的酒店
3. 搜索完成后，从结果中挑选最合适的一家，输出结构化 JSON

**输出要求（严格遵守）：**
1. 搜索完成后，只输出一个合法的 JSON 对象（单个酒店），不要输出数组，不要输出任何额外文字。
2. 字段定义如下（字段名和类型必须完全一致）：
   - name (string): 酒店名称
   - address (string): 酒店地址
   - location (object|null): 经纬度，包含 longitude (float) 和 latitude (float)，没有则为 null
   - price_range (string): 价格范围，如"300-500元/晚"
   - rating (string): 评分
   - distance (string): 距离当天主要景点的距离，如"1.2公里"
   - type (string): 酒店类型，如"经济型"、"豪华型"等
   - estimated_cost (int): 预估费用，单位为元/晚

**规划约束：**
1. 优先推荐距离当天景点较近的酒店
2. 符合用户的预算水平和酒店偏好
3. 不同天可以推荐同一家酒店（如果位置合理）
"""

DAILY_DINING_PLAN_PROMPT = """你是餐饮规划专家。你的任务是为旅行的**指定一天**推荐合适的餐饮。

**输出要求（严格遵守）：**
1. 只输出一个合法的 JSON 数组，不要输出任何额外文字。
2. 数组中每个元素代表一顿餐饮，字段定义如下（字段名和类型必须完全一致）：
   - type (string): 餐饮类型，必须为 "breakfast"、"lunch"、"dinner" 或 "snack" 之一
   - name (string): 餐厅名称或推荐菜品
   - address (string|null): 餐厅地址，没有则为 null
   - location (object|null): 经纬度，包含 longitude (float) 和 latitude (float)，没有则为 null
   - description (string|null): 推荐理由或特色菜品描述
   - estimated_cost (int): 预估人均费用，单位为元

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


# ============================================================
# Phase1: 搜索类 Agent 实现
# ============================================================

class AttractionSearchAgent(EnhancedAgent):
    """景点搜索智能体 - 调用高德 MCP 搜索景点原始数据"""

    def __init__(
        self,
        llm: LLMClient,
        state,
        tool_registry: ToolRegistry,
        context_manager: Optional[ContextManager] = None,
        user_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        super().__init__(
            name="景点搜索专家",
            llm=llm,
            state=state,
            system_prompt=ATTRACTION_SEARCH_PROMPT,
            tool_registry=tool_registry,
            enable_tool_calling=True,
            context_manager=context_manager,
            user_id=user_id,
            memory_manager=memory_manager
        )

    def run(self, input_text: str, **kwargs) -> str:
        """运行景点搜索"""
        if self.context_manager:
            request_context = self.context_manager.get_shared_data("request")
            if request_context:
                preferences = request_context.get("preferences", [])
                if preferences and "景点" not in input_text.lower():
                    pref_keywords = ", ".join(preferences[:2])
                    input_text = f"{input_text}，优先搜索{pref_keywords}相关的景点"

        result = super().run(input_text, **kwargs)

        if self.context_manager:
            self.context_manager.share_data(
                "attraction_locations",
                result,
                from_agent=self.name
            )

        return result


class WeatherQueryAgent(EnhancedAgent):
    """天气查询智能体 - 调用高德 MCP 查询天气"""

    def __init__(
        self,
        llm: LLMClient,
        state,
        tool_registry: ToolRegistry,
        context_manager: Optional[ContextManager] = None,
        user_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        super().__init__(
            name="天气查询专家",
            llm=llm,
            state=state,
            system_prompt=WEATHER_SEARCH_PROMPT,
            tool_registry=tool_registry,
            enable_tool_calling=True,
            context_manager=context_manager,
            user_id=user_id,
            memory_manager=memory_manager
        )

    def run(self, input_text: str, **kwargs) -> str:
        """运行天气查询"""
        if self.context_manager:
            request_context = self.context_manager.get_shared_data("request")
            if request_context:
                start_date = request_context.get("start_date")
                end_date = request_context.get("end_date")
                if start_date and end_date:
                    input_text = f"{input_text}，查询日期范围：{start_date} 到 {end_date}"

        result = super().run(input_text, **kwargs)

        if self.context_manager:
            self.context_manager.share_data(
                "weather_info",
                result,
                from_agent=self.name
            )

        return result


# ============================================================
# Phase2: 按天规划类 Agent 实现
# ============================================================

class DailyAttractionPlanAgent(EnhancedAgent):
    """单日景点规划智能体 - 从候选景点中为指定一天挑选并安排景点"""

    def __init__(
        self,
        llm: LLMClient,
        state,
        context_manager: Optional[ContextManager] = None,
        user_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        super().__init__(
            name="单日景点规划专家",
            llm=llm,
            state=state,
            system_prompt=DAILY_ATTRACTION_PLAN_PROMPT,
            tool_registry=None,
            enable_tool_calling=False,
            context_manager=context_manager,
            user_id=user_id,
            memory_manager=memory_manager
        )


class DailyHotelPlanAgent(EnhancedAgent):
    """单日酒店规划智能体 - 根据当天景点位置动态搜索附近酒店并推荐"""

    def __init__(
        self,
        llm: LLMClient,
        state,
        tool_registry: Optional[ToolRegistry] = None,
        context_manager: Optional[ContextManager] = None,
        user_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        super().__init__(
            name="单日酒店规划专家",
            llm=llm,
            state=state,
            system_prompt=DAILY_HOTEL_PLAN_PROMPT,
            tool_registry=tool_registry,
            enable_tool_calling=True,
            context_manager=context_manager,
            user_id=user_id,
            memory_manager=memory_manager
        )


class DailyDiningPlanAgent(EnhancedAgent):
    """单日餐饮规划智能体 - 为指定一天推荐餐饮"""

    def __init__(
        self,
        llm: LLMClient,
        state,
        context_manager: Optional[ContextManager] = None,
        user_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        super().__init__(
            name="单日餐饮规划专家",
            llm=llm,
            state=state,
            system_prompt=DAILY_DINING_PLAN_PROMPT,
            tool_registry=None,
            enable_tool_calling=False,
            context_manager=context_manager,
            user_id=user_id,
            memory_manager=memory_manager
        )


class TripThemeAgent(EnhancedAgent):
    """行程标题与主题生成智能体 - 为整个行程生成标题和每天主题"""

    def __init__(
        self,
        llm: LLMClient,
        state,
        context_manager: Optional[ContextManager] = None,
        user_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        super().__init__(
            name="行程主题专家",
            llm=llm,
            state=state,
            system_prompt=DAILY_THEME_PROMPT,
            tool_registry=None,
            enable_tool_calling=False,
            context_manager=context_manager,
            user_id=user_id,
            memory_manager=memory_manager
        )
