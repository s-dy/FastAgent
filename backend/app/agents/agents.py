import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, TypedDict

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END

from app.models import Budget, TripPlanRequest, TripPlanResponse, DailyPlan
from app.observability.logger import default_logger as logger

from .utils.tools_manager import ToolsManager
from .utils.parser import parse_json_response
from .utils.budget import calculate_daily_budget, check_budget_compliance, BUDGET_RANGES
from .utils.converters import dict_to_attraction, dict_to_hotel, dict_to_meal
from .utils.prompts import (
    get_weather_for_date,
    format_weather_to_text,
    calculate_current_date,
    filter_unassigned_attractions,
    build_daily_attraction_prompt,
    build_daily_hotel_prompt,
    build_daily_dining_prompt,
    build_theme_prompt,
    DAILY_ATTRACTION_PLAN_PROMPT,
    DAILY_HOTEL_PLAN_PROMPT,
    DAILY_DINING_PLAN_PROMPT,
    DAILY_THEME_PROMPT,
)
from .utils.llm import invoke_llm_with_system
from .utils.validators import validate_and_filter_daily_plan, validate_adjacent_days
from app.services.user_profile_service import user_profile_service
from app.services.trip_memory_service import trip_memory_service, TripMemoryService
from app.utils import _run_async


# ============================================================
# State 定义
# ============================================================
class TripPlanState(TypedDict):
    """LangGraph 图的全局状态"""
    # 输入
    request: Dict[str, Any] # 请求
    user_id: str # 用户ID
    request_id: str # 请求ID

    # Phase1 搜索结果
    raw_attractions: list # 景点搜索结果
    raw_weather: list # 天气搜索结果

    # Phase2 按天规划中间数据
    current_day: int # 当前天数
    duration: int # 行程天数
    assigned_attraction_names: List[str] # 已分配景点
    assigned_dining_names: List[str] # 已分配美食
    daily_plans: List[Dict[str, Any]] # 按天规划
    daily_summaries: List[str] # 按天规划总结

    # 长期记忆
    memory_context: str # 合并后的记忆上下文文本，注入到各 Agent 的 Prompt 中
    user_profile: Dict[str, Any] # 用户偏好画像（结构化数据，用于程序化过滤）

    # Phase3 最终结果
    trip_title: str # 行程标题
    daily_themes: List[str] # 按天规划主题
    total_budget: Dict[str, Any] # 总预算
    final_response: Optional[Dict[str, Any]] # 最终结果

# ============================================================
# 工具加载与
# ============================================================
def _load_tools() -> List[BaseTool]:
    try:
        tools_manager = ToolsManager()
        client = MultiServerMCPClient({
            "amap": {
                "url": "https://mcp.amap.com/mcp?key=" + os.getenv("AMAP_MCP_KEY", ""),
                "transport": "http",
            },
            "hotel": {
                "url": "http://127.0.0.1:8000/mcp",
                "transport": "http",
            },
        })
        tools_manager.register_tools(client)
        logger.info(f"✅ [MCP] 成功加载 MCP 工具: {tools_manager.get_tool_names()}")
        return tools_manager.get_tools()
    except Exception as load_error:
        logger.error(f"❌ [MCP] 加载 MCP 工具失败: {load_error}")
        return []
# ============================================================
# LangGraph 节点函数
# ============================================================
def node_load_memory(state: TripPlanState) -> dict:
    """
    记忆加载节点：在规划开始前一次性加载长期记忆。

    1. 从 Redis 读取用户偏好画像
    2. 从 Milvus 检索相关情景记忆（最多 3 条）
    3. 合并为 memory_context 文本，写入 State
    """
    user_id = state["user_id"]
    request = state["request"]
    destination = request["destination"]
    preferences = request.get("preferences", [])

    logger.info(f"🧠 [Memory] 加载用户长期记忆: user_id={user_id}, dest={destination}")

    # 1. 加载用户偏好画像
    user_profile = user_profile_service.get_profile(user_id)

    # 2. 构建偏好画像的文本上下文
    profile_context = user_profile_service.build_memory_context(user_id, destination)

    # 3. 检索情景记忆的文本上下文
    episodic_context = trip_memory_service.build_memory_context(user_id, destination, preferences, limit=3)

    # 4. 合并为完整的 memory_context
    context_parts = []
    if profile_context:
        context_parts.append(profile_context)
    if episodic_context:
        context_parts.append(episodic_context)

    memory_context = "\n".join(context_parts)

    if memory_context:
        logger.info(f"✅ [Memory] 记忆加载完成，memory_context 长度: {len(memory_context)}")
    else:
        logger.info("ℹ️ [Memory] 无历史记忆，首次使用")

    return {
        "memory_context": memory_context,
        "user_profile": user_profile,
    }

def node_search_parallel(state: TripPlanState) -> dict:
    """
    Phase1 节点：通过高德 MCP 工具并行搜索景点和天气。

    使用 RunnableParallel + RunnableLambda 包装 MCP 工具调用，
    让景点搜索和天气查询两个 ReAct Agent 并行执行。
    每个 Agent 内部通过 _invoke_llm_with_mcp_tools 实现多轮工具调用。
    """
    request = state["request"]
    destination = request["destination"]
    preferences = request.get("preferences", [])
    start_date = request["start_date"]
    end_date = request["end_date"]

    logger.info("🚀 开始通过高德 MCP 并行搜索景点和天气...")

    keywords = preferences[0] if preferences else "景点"

    # 使用用户画像过滤已去过的景点
    visited_attractions = set(state.get("user_profile", {}).get("visited_attractions", []))

    def attractions_parser(raw_attractions: list) -> list:
        for attraction in raw_attractions:
            if attraction["type"] == "text":
                pois = json.loads(attraction['text']).get("pois", [])
                return [{"id": poi["id"], "name": poi["name"], "address": poi["address"]} for poi in pois]
        return []

    def weather_parser(raw_weather: list) -> list:
        for weather in raw_weather:
            if weather["type"] == "text":
                return json.loads(weather['text']).get("forecasts", [])
        return []

    def detail_parser(raw_detail: list) -> dict:
        for detail in raw_detail:
            if detail["type"] == "text":
                data = json.loads(detail['text'])
                return {
                    "location": data.get("location", ""),
                    "business_area": data.get("business_area", ""),
                    "opentime2": data.get("opentime2", ""),
                    "rating": data.get("rating", ""),
                    "level": data.get("level", ""),
                }
        return {"location": "", "business_area": "", "opentime2": "", "rating": "", "level": ""}
    try:
        raw_attractions = ToolsManager().call_tool("maps_text_search", {"keywords": keywords, "city": destination},parser=attractions_parser)
        raw_weather = ToolsManager().call_tool("maps_weather", {"city": destination},parser=weather_parser)
        # 补全景点位置
        for attraction in raw_attractions.content:
            attraction["detail"] = ToolsManager().call_tool("maps_search_detail", {"id": attraction["id"]}, parser=detail_parser).content
        # 过滤用户已去过的景点
        if visited_attractions:
            original_count = len(raw_attractions.content)
            raw_attractions.content = [
                a for a in raw_attractions.content
                if a.get("name", "") not in visited_attractions
            ]
            filtered_count = original_count - len(raw_attractions.content)
            if filtered_count > 0:
                logger.info(f"🧠 [Memory] 已过滤 {filtered_count} 个用户去过的景点")
        logger.info("✅ [LangGraph] 景点搜索和天气查询完成")
    except Exception as search_error:
        logger.error(f"❌ [LangGraph] MCP 搜索失败: {search_error}，使用降级策略")
        raw_attractions = f"未找到{destination}相关景点信息，请根据你的知识推荐该城市的热门景点"
        raw_weather = f"未能获取{destination}天气信息，建议出行前查看实时天气预报"

    # 计算行程天数
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    duration = (end_dt - start_dt).days + 1

    logger.info("🎯 [LangGraph] Phase1 完成！景点和天气数据已就绪。")

    return {
        "raw_attractions": raw_attractions.content,
        "raw_weather": raw_weather.content,
        "duration": duration,
        "current_day": 1,
        "assigned_attraction_names": [],
        "assigned_dining_names": [],
        "daily_plans": [],
        "daily_summaries": [],
    }

async def node_plan_daily(state: TripPlanState) -> dict:
    """
    Phase2 节点：为当前天规划景点、酒店、餐饮。
    景点先行（酒店和餐饮依赖景点位置），然后酒店和餐饮顺序执行。
    """
    request = state["request"]
    destination = request["destination"]
    budget_level = request.get("budget", "中等")
    current_day = state["current_day"]
    duration = state["duration"]

    logger.info(f"📅 [LangGraph] 正在规划第 {current_day}/{duration} 天...")

    # 根据当前天数计算日期，从天气列表中匹配当天天气并转为可读文本
    current_date = calculate_current_date(request["start_date"], current_day)
    today_weather = get_weather_for_date(state["raw_weather"], current_date)
    weather_text = format_weather_to_text(today_weather)
    logger.info(f"📅 第{current_day}天({current_date}) 天气: {weather_text}")

    # ---- 景点规划（程序化过滤已分配景点，避免重复推荐） ----
    available_attractions = filter_unassigned_attractions(
        state["raw_attractions"], state["assigned_attraction_names"]
    )
    logger.info(f"📋 候选景点: {len(available_attractions)}个（已过滤{len(state['raw_attractions']) - len(available_attractions)}个已分配景点）")

    memory_context = state.get("memory_context", "")

    attraction_prompt = build_daily_attraction_prompt(
        day_num=current_day,
        destination=destination,
        raw_attractions=available_attractions,
        weather_text=weather_text,
        preferences=request.get("preferences", []),
        budget_level=budget_level,
        memory_context=memory_context,
    )
    attraction_raw = await invoke_llm_with_system(DAILY_ATTRACTION_PLAN_PROMPT, attraction_prompt)

    try:
        attractions_data = parse_json_response(attraction_raw)
        if not isinstance(attractions_data, list):
            attractions_data = [attractions_data]
    except (json.JSONDecodeError, Exception) as parse_error:
        logger.error(f"❌ [LangGraph] 第{current_day}天景点规划 JSON 解析失败: {parse_error}")
        attractions_data = []

    # 构建景点摘要
    attraction_names_for_summary = []
    for attraction in attractions_data:
        name = attraction.get("name", "未知景点")
        location = attraction.get("location", {})
        attraction_names_for_summary.append(
            f"{name}(经度:{location.get('longitude', '?')}, 纬度:{location.get('latitude', '?')})"
        )
    day_attractions_summary = "、".join(attraction_names_for_summary) if attraction_names_for_summary else "暂无景点信息"

    # ---- 酒店规划----
    hotel_prompt = build_daily_hotel_prompt(
        start_date=current_date,
        day_num=current_day,
        destination=destination,
        day_attractions_summary=day_attractions_summary,
        budget_level=budget_level,
        hotel_preferences=request.get("hotel_preferences", []),
        memory_context=memory_context,
    )
    hotel_raw = await invoke_llm_with_system(DAILY_HOTEL_PLAN_PROMPT, hotel_prompt, use_tool=True, max_tool_iterations=4)

    hotel_data = {}
    try:
        hotel_data = parse_json_response(hotel_raw)
        if isinstance(hotel_data, list):
            hotel_data = hotel_data[0] if hotel_data else {}
    except (json.JSONDecodeError, Exception) as parse_error:
        logger.error(f"❌ [LangGraph] 第{current_day}天酒店规划解析失败: {parse_error}")

    # ---- 餐饮规划 ----
    dining_prompt = build_daily_dining_prompt(
        day_num=current_day,
        destination=destination,
        day_attractions_summary=day_attractions_summary,
        budget_level=budget_level,
        assigned_dining_names=state["assigned_dining_names"],
        memory_context=memory_context,
    )
    dining_raw = await invoke_llm_with_system(DAILY_DINING_PLAN_PROMPT, dining_prompt, use_tool=True, max_tool_iterations=4)

    dining_data = []
    try:
        dining_data = parse_json_response(dining_raw)
        if not isinstance(dining_data, list):
            dining_data = [dining_data]
    except (json.JSONDecodeError, Exception) as parse_error:
        logger.error(f"❌ [LangGraph] 第{current_day}天餐饮规划解析失败: {parse_error}")

    # ---- 转换为 Pydantic 模型 ----
    attractions = [m for m in (dict_to_attraction(d) for d in attractions_data) if m]
    hotels = [dict_to_hotel(hotel_data)] if hotel_data and dict_to_hotel(hotel_data) else []
    dining = [m for m in (dict_to_meal(d) for d in dining_data) if m]

    # ---- 计算预算 ----
    daily_budget = calculate_daily_budget(attractions_data, hotel_data, dining_data, budget_level)
    check_budget_compliance(daily_budget, budget_level, current_day)

    # ---- 组装 DailyPlan ----
    daily_plan = DailyPlan(
        day=current_day,
        theme="",
        weather=None,
        hotels=hotels,
        attractions=attractions,
        dining=dining,
        budget=daily_budget,
    )
    daily_plan = validate_and_filter_daily_plan(daily_plan, destination)

    # ---- 更新已分配列表 ----
    new_assigned_attractions = list(state["assigned_attraction_names"])
    for attraction in daily_plan.attractions:
        new_assigned_attractions.append(attraction.name)

    new_assigned_dining = list(state["assigned_dining_names"])
    for meal in daily_plan.dining:
        new_assigned_dining.append(meal.name)

    # 生成当天摘要
    attraction_names = [a.name for a in daily_plan.attractions]
    day_summary = "、".join(attraction_names) if attraction_names else "休息日"

    new_daily_plans = list(state["daily_plans"])
    new_daily_plans.append(daily_plan.model_dump())

    new_daily_summaries = list(state["daily_summaries"])
    new_daily_summaries.append(day_summary)

    logger.info(
        f"✅ [LangGraph] 第 {current_day} 天规划完成: {len(daily_plan.attractions)} 个景点, "
        f"{len(daily_plan.hotels)} 个酒店, {len(daily_plan.dining)} 个餐饮"
    )

    return {
        "current_day": current_day + 1,
        "assigned_attraction_names": new_assigned_attractions,
        "assigned_dining_names": new_assigned_dining,
        "daily_plans": new_daily_plans,
        "daily_summaries": new_daily_summaries,
    }


def should_continue_planning(state: TripPlanState) -> str:
    """条件边：判断是否还有天数需要规划"""
    if state["current_day"] <= state["duration"]:
        return "plan_daily"
    return "generate_theme"


async def node_generate_theme(state: TripPlanState) -> dict:
    """Phase3 节点：生成行程标题和每天主题"""
    request = state["request"]
    destination = request["destination"]
    duration = state["duration"]

    logger.info("🚀 [LangGraph] Phase3: 生成标题和主题...")

    # 验证相邻天景点距离
    daily_plan_models = [DailyPlan(**dp) for dp in state["daily_plans"]]
    validate_adjacent_days(daily_plan_models)

    logger.info("🎯 [LangGraph] Phase2 完成！所有天数规划已就绪。")

    theme_prompt = build_theme_prompt(destination, duration, state["daily_summaries"])
    theme_raw = await invoke_llm_with_system(DAILY_THEME_PROMPT, theme_prompt)

    trip_title = f"{destination}{duration}日游"
    daily_themes = []
    try:
        theme_data = parse_json_response(theme_raw)
        trip_title = theme_data.get("trip_title", trip_title)
        daily_themes = theme_data.get("daily_themes", [])
    except (json.JSONDecodeError, Exception) as theme_error:
        logger.error(f"❌ [LangGraph] 标题/主题生成解析失败: {theme_error}，使用默认标题")

    return {
        "trip_title": trip_title,
        "daily_themes": daily_themes,
    }


def node_assemble_response(state: TripPlanState) -> dict:
    """Phase3 节点：计算总预算 + 拼装最终响应"""
    request = state["request"]
    budget_level = request.get("budget", "中等")
    duration = state["duration"]
    request_id = state["request_id"]

    logger.info("🚀 [LangGraph] 计算总预算并拼装最终响应...")

    # 重建 DailyPlan 模型列表
    daily_plans = [DailyPlan(**dp) for dp in state["daily_plans"]]

    # 写入主题
    daily_themes = state.get("daily_themes", [])
    for idx, daily_plan in enumerate(daily_plans):
        if idx < len(daily_themes):
            daily_plan.theme = daily_themes[idx]
        else:
            daily_plan.theme = f"第{idx + 1}天行程"

    # 计算总预算
    total_attraction_ticket_cost = sum(day.budget.attraction_ticket_cost for day in daily_plans)
    total_hotel_cost = sum(day.budget.hotel_cost for day in daily_plans)
    total_dining_cost = sum(day.budget.dining_cost for day in daily_plans)
    total_transport_cost = sum(day.budget.transport_cost for day in daily_plans)
    total_cost = total_attraction_ticket_cost + total_hotel_cost + total_dining_cost + total_transport_cost

    budget_info = BUDGET_RANGES.get(budget_level, BUDGET_RANGES["中等"])
    total_daily_max = budget_info["daily_total_max"] * duration
    is_total_over_budget = total_cost > total_daily_max

    if is_total_over_budget:
        logger.warning(
            f"⚠️ [LangGraph] 总预算超标: 实际 {total_cost:.0f}元, "
            f"预算等级「{budget_level}」{duration}天上限 {total_daily_max}元"
        )

    total_budget = Budget(
        attraction_ticket_cost=total_attraction_ticket_cost,
        hotel_cost=total_hotel_cost,
        dining_cost=total_dining_cost,
        transport_cost=total_transport_cost,
        total=total_cost,
        budget_level=budget_level,
        is_over_budget=is_total_over_budget,
    )

    # 拼装最终响应
    validated_plan = TripPlanResponse(
        id=request_id,
        trip_title=state.get("trip_title", f"{request['destination']}{duration}日游"),
        total_budget=total_budget,
        days=daily_plans,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    logger.info(f"🎉 [LangGraph] 成功生成行程计划: {validated_plan.trip_title}")

    return {
        "final_response": validated_plan.model_dump(),
    }

def node_save_memory(state: TripPlanState) -> dict:
    """
    记忆存储节点：规划完成后持久化长期记忆。

    1. 增量更新用户偏好画像到 Redis
    2. 存储本次行程的自然语言摘要到 Milvus 向量库
    """
    user_id = state["user_id"]
    request = state["request"]
    final_response = state.get("final_response")

    if not final_response:
        logger.warning("⚠️ [Memory] 无最终结果，跳过记忆存储")
        return {}

    logger.info(f"💾 [Memory] 开始存储长期记忆: user_id={user_id}")

    destination = request.get("destination", "")
    preferences = request.get("preferences", [])
    budget_level = request.get("budget", "中等")
    hotel_preferences = request.get("hotel_preferences", [])
    start_date = request.get("start_date", "")
    duration = state["duration"]

    # 从 final_response 中提取景点和酒店名称
    days_data = final_response.get("days", [])
    all_attraction_names = []
    all_hotel_names = []
    for day_data in days_data:
        for attraction in day_data.get("attractions", []):
            name = attraction.get("name", "")
            if name:
                all_attraction_names.append(name)
        for hotel in day_data.get("hotels", []):
            name = hotel.get("name", "")
            if name:
                all_hotel_names.append(name)

    total_budget_data = final_response.get("total_budget", {})
    actual_total_cost = total_budget_data.get("total", 0.0)
    is_over_budget = total_budget_data.get("is_over_budget", False)

    # 1. 更新用户偏好画像
    try:
        user_profile_service.update_after_trip(
            user_id=user_id,
            destination=destination,
            preferences=preferences,
            budget_level=budget_level,
            hotel_preferences=hotel_preferences,
            attraction_names=all_attraction_names,
            actual_total_cost=actual_total_cost,
            trip_days=duration,
        )
    except Exception as profile_error:
        logger.error(f"❌ [Memory] 更新用户画像失败: {profile_error}")

    # 2. 存储情景记忆
    try:
        memory_text = TripMemoryService.build_trip_summary(
            destination=destination,
            start_date=start_date,
            duration=duration,
            preferences=preferences,
            budget_level=budget_level,
            attraction_names=all_attraction_names,
            hotel_names=all_hotel_names,
            total_cost=actual_total_cost,
            is_over_budget=is_over_budget,
        )
        trip_memory_service.save_trip_memory(
            user_id=user_id,
            memory_text=memory_text,
            destination=destination,
            trip_date=start_date,
        )
    except Exception as memory_error:
        logger.error(f"❌ [Memory] 存储情景记忆失败: {memory_error}")

    logger.info("✅ [Memory] 长期记忆存储完成")
    return {}

# ============================================================
# 构建 LangGraph 图
# ============================================================
def build_trip_planner_graph() -> StateGraph:
    """
    构建旅行规划的 LangGraph 图。

    图结构:
        START → load_memory → search_parallel → plan_daily (循环) → generate_theme → assemble_response → save_memory → END

    plan_daily 节点通过条件边实现按天循环：
        - 如果 current_day <= duration → 继续 plan_daily
        - 否则 → 进入 generate_theme
    """
    graph = StateGraph(TripPlanState)

    # 添加节点
    graph.add_node("load_memory", node_load_memory)
    graph.add_node("search_parallel", node_search_parallel)
    graph.add_node("plan_daily", node_plan_daily)
    graph.add_node("generate_theme", node_generate_theme)
    graph.add_node("assemble_response", node_assemble_response)
    graph.add_node("save_memory", node_save_memory)

    # 添加边
    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "search_parallel")
    graph.add_edge("search_parallel", "plan_daily")

    # 条件边：按天循环
    graph.add_conditional_edges(
        "plan_daily",
        should_continue_planning,
        {
            "plan_daily": "plan_daily",
            "generate_theme": "generate_theme",
        },
    )

    graph.add_edge("generate_theme", "assemble_response")
    graph.add_edge("assemble_response", "save_memory")
    graph.add_edge("save_memory", END)

    return graph


# ============================================================
# 入口类
# ============================================================

class TripPlannerGraph:
    """
    基于 LangGraph 的旅行规划助手入口类。
    与原 PlannerAgent 接口一致，提供 plan_trip 方法。
    """

    def __init__(self):
        graph_builder = build_trip_planner_graph()
        self.graph = graph_builder.compile()
        _load_tools()

    def plan_trip(
        self,
        request: TripPlanRequest,
        user_id: str,
    ) -> Optional[TripPlanResponse]:
        """
        规划行程 - 通过 LangGraph 图执行三阶段流程。

        Args:
            request: 行程规划请求
            user_id: 用户ID

        Returns:
            行程规划响应，失败返回 None
        """
        request_id = f"lg_{datetime.now().timestamp()}"

        initial_state: TripPlanState = {
            "request": request.model_dump(),
            "user_id": user_id,
            "request_id": request_id,
            "raw_attractions": "",
            "raw_weather": "",
            "current_day": 1,
            "duration": 0,
            "assigned_attraction_names": [],
            "assigned_dining_names": [],
            "daily_plans": [],
            "daily_summaries": [],
            "memory_context": "",
            "user_profile": {},
            "trip_title": "",
            "daily_themes": [],
            "total_budget": {},
            "final_response": None,
        }

        try:
            logger.info(f"🚀 [LangGraph] 开始规划行程: {request.destination}")
            final_state = _run_async(self.graph.ainvoke(initial_state))

            if final_state.get("final_response"):
                return TripPlanResponse(**final_state["final_response"])
            return None

        except Exception as planning_error:
            logger.error(
                f"[LangGraph] 行程规划失败: {planning_error}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "destination": request.destination,
                },
            )
            return None
