from typing import Optional
from fastagent.core import LLMClient
from fastagent.tools import ToolRegistry
from fastagent.memory import MemoryConfig, MemoryManager
from app.agents.fastagent.enhanced_agent import EnhancedAgent
from app.services.context_manager import ContextManager


# ============================================================
# Phase1: 搜索类 Agent 提示词
# ============================================================

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
