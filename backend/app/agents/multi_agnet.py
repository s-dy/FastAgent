"""
静态规划架构 + 动态信息补全（协调器-工作器模式）
基于 LangGraph 的 Send API 实现协调器-工作器架构

核心思想：
1. 协调器（Orchestrator）：分解任务、委派给工作节点、合成最终结果
2. 工作节点（Workers）：独立执行子任务（景点搜索、天气查询、每日规划）
3. Send API：动态创建工作节点并发送特定输入
4. 共享状态：使用 operator.add reducer 让所有工作节点并行写入
"""
import os
from typing import Dict, List, Optional, Any, TypedDict, Annotated, Literal
from datetime import datetime
from operator import add

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from pydantic import BaseModel, Field

from app.models.trip import TripPlanRequest, TripPlanResponse, DailyPlan
from app.models.common import Hotel, Attraction, Meal, Budget
from app.observability.logger import default_logger as logger
from app.agents.utils.llm import invoke_llm_with_system
from app.agents.utils.tools_manager import ToolsManager
from app.agents.utils.prompts import (
    ATTRACTION_SEARCH_PROMPT,
    WEATHER_SEARCH_PROMPT,
    DAILY_ATTRACTION_PLAN_PROMPT,
    DAILY_HOTEL_PLAN_PROMPT,
    DAILY_DINING_PLAN_PROMPT,
    DAILY_THEME_PROMPT,
    get_weather_for_date,
    format_weather_to_text,
    calculate_current_date,
    filter_unassigned_attractions,
    build_daily_attraction_prompt,
    build_daily_hotel_prompt,
    build_daily_dining_prompt,
    build_theme_prompt,
)
from app.agents.utils.converters import dict_to_attraction, dict_to_hotel, dict_to_meal
from app.agents.utils.validators import validate_and_filter_daily_plan, validate_adjacent_days
from app.agents.workflow_agents import (
    parse_json_response,
    calculate_daily_budget,
    BUDGET_RANGES,
)

def _load_tools() -> List[BaseTool]:
    try:
        tools_manager = ToolsManager()
        client = MultiServerMCPClient({
            "amap": {
                "url": "https://mcp.amap.com/mcp?key=" + os.getenv("AMAP_MCP_KEY", ""),
                "transport": "http",
            },
            "hotel": {
                "url": "http://127.0.0.1:8999/mcp",
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
# 主状态定义
# ============================================================

class TripSection(BaseModel):
    """行程的每个部分"""
    task_type: str  # "attraction_search", "weather_search", "daily_planning"
    description: str  # 任务描述
    task_input: Dict[str, Any]  # 任务输入参数
    day_num: Optional[int] = None  # 如果是每日规划，记录天数

class CoordinatorState(TypedDict):
    """协调器主状态"""
    request_id: str
    request: Dict[str, Any]
    user_id: str
    destination: str
    duration: int
    budget_level: str
    start_date: str
    preferences: List[str]
    hotel_preferences: List[str]

    # 行程计划（由 orchestrator 生成）
    sections: List[TripSection]

    # 工作节点完成的任务（共享状态键，所有工作节点并行写入）
    completed_tasks: Annotated[List[Dict[str, Any]], add]

    # 原始数据
    raw_attractions: List[Dict[str, Any]]
    raw_weather: List[Dict[str, Any]]

    # 最终输出
    final_response: Optional[Dict[str, Any]]

# ============================================================
# 工作节点状态定义
# ============================================================

class AttractionSearchWorkerState(TypedDict):
    """景点搜索工作节点状态"""
    task_input: Dict[str, Any]
    completed_tasks: Annotated[List[Dict[str, Any]], add]  # 用于合并结果

class WeatherSearchWorkerState(TypedDict):
    """天气查询工作节点状态"""
    task_input: Dict[str, Any]
    completed_tasks: Annotated[List[Dict[str, Any]], add]

class DailyPlanningWorkerState(TypedDict):
    """每日规划工作节点状态"""
    task_input: Dict[str, Any]
    completed_tasks: Annotated[List[Dict[str, Any]], add]

# ============================================================
# 协调器节点
# ============================================================

async def orchestrator_node(state: CoordinatorState) -> Dict[str, Any]:
    """
    协调器节点：生成行程计划
    """
    request = state["request"]
    destination = request["destination"]
    duration = state["duration"]
    preferences = request.get("preferences", [])
    hotel_preferences = request.get("hotel_preferences", [])

    logger.info(f"🎯 [Orchestrator] 开始生成行程计划...")

    # 检查已完成的任务
    completed_tasks = state.get("completed_tasks", [])
    completed_types = [t.get("task_type") for t in completed_tasks]
    completed_days = set()
    for task in completed_tasks:
        if task.get("task_type") == "daily_planning" and task.get("day_num"):
            completed_days.add(task.get("day_num"))

    logger.info(f"🎯 [Orchestrator] 已完成任务: {completed_types}")
    logger.info(f"🎯 [Orchestrator] 已完成天数: {sorted(completed_days)}")

    # 生成行程计划
    sections = []

    # 阶段1：景点搜索和天气查询（如果还没完成）
    if "attraction_search" not in completed_types:
        sections.append(TripSection(
            task_type="attraction_search",
            description=f"搜索{destination}的景点信息",
            task_input={
                "destination": destination,
                "preferences": preferences,
            }
        ))

    if "weather_search" not in completed_types:
        sections.append(TripSection(
            task_type="weather_search",
            description=f"查询{destination}的天气信息",
            task_input={
                "destination": destination,
            }
        ))

    # 如果阶段1已完成，生成阶段2的每日规划任务
    if "attraction_search" in completed_types and "weather_search" in completed_types:
        # 从共享状态中获取景点和天气数据
        raw_attractions = state.get("raw_attractions", [])
        raw_weather = state.get("raw_weather", [])

        logger.info(f"🎯 [Orchestrator] 阶段1已完成，生成每日规划任务")
        logger.info(f"🎯 [Orchestrator] 可用数据: {len(raw_attractions)} 个景点, {len(raw_weather)} 条天气")

        # 预先分配景点到每天
        day_attraction_mapping = _allocate_attractions_to_days(raw_attractions, duration)

        # 为未完成的天生成任务
        for day_num in range(1, duration + 1):
            if day_num not in completed_days:
                sections.append(TripSection(
                    task_type="daily_planning",
                    description=f"规划第{day_num}天行程",
                    task_input={
                        "day_num": day_num,
                        "destination": destination,
                        "preferences": preferences,
                        "hotel_preferences": hotel_preferences,
                        "budget_level": state.get("budget_level", "中等"),
                        "start_date": state.get("start_date", datetime.now().strftime("%Y-%m-%d")),
                        "assigned_attraction_names": state.get("assigned_attraction_names", []),
                        "assigned_dining_names": state.get("assigned_dining_names", []),
                        "raw_attractions": day_attraction_mapping.get(day_num, []),
                        "raw_weather": raw_weather,
                    }
                ))

    logger.info(f"🎯 [Orchestrator] 行程计划生成完成，共 {len(sections)} 个部分")

    # 返回生成的计划
    return {"sections": sections}

# ============================================================
# 条件边函数：分配工作节点
# ============================================================

def assign_workers(state: CoordinatorState) -> List[Send]:
    """
    条件边函数：为每个行程部分创建工作节点
    """
    sections = state.get("sections", [])

    logger.info(f"📋 [Assign Workers] 为 {len(sections)} 个行程部分创建工作节点...")

    # 根据任务类型创建不同的 worker
    sends = []
    for section in sections:
        if section.task_type == "attraction_search":
            sends.append(Send(
                "attraction_search_worker",
                {
                    "task_input": section.task_input,
                    "completed_tasks": []
                }
            ))
        elif section.task_type == "weather_search":
            sends.append(Send(
                "weather_search_worker",
                {
                    "task_input": section.task_input,
                    "completed_tasks": []
                }
            ))
        elif section.task_type == "daily_planning":
            sends.append(Send(
                "daily_planning_worker",
                {
                    "task_input": section.task_input,
                    "completed_tasks": []
                }
            ))

    return sends

def _allocate_attractions_to_days(attractions: List[Dict[str, Any]], duration: int) -> Dict[int, List[Dict[str, Any]]]:
    """
    将景点均匀分配到每一天
    """
    if not attractions:
        return {}

    total_attractions = len(attractions)
    attractions_per_day = max(2, min(4, total_attractions // duration))

    import random
    shuffled_attractions = attractions.copy()
    random.shuffle(shuffled_attractions)

    day_attraction_mapping = {}
    for day_num in range(1, duration + 1):
        start_idx = (day_num - 1) * attractions_per_day
        end_idx = start_idx + attractions_per_day

        if start_idx >= total_attractions:
            day_attraction_mapping[day_num] = []
        elif end_idx > total_attractions:
            day_attraction_mapping[day_num] = shuffled_attractions[start_idx:]
        else:
            day_attraction_mapping[day_num] = shuffled_attractions[start_idx:end_idx]

    return day_attraction_mapping

# ============================================================
# 景点搜索工作节点
# ============================================================

async def attraction_search_worker(state: AttractionSearchWorkerState) -> Dict[str, Any]:
    """
    景点搜索工作节点
    """
    task_input = state.get("task_input")
    destination = task_input["destination"]
    preferences = task_input.get("preferences", [])

    logger.info(f"🔧 [Attraction Worker] 开始搜索 {destination} 的景点...")

    # 构建搜索关键词
    keywords = preferences[1] if len(preferences) > 1 else "热门景点"

    # # 调用 LLM 搜索景点
    # attraction_prompt = f"请搜索 {destination} 的{keywords}"
    # attraction_raw = await invoke_llm_with_system(
    #     ATTRACTION_SEARCH_PROMPT,
    #     attraction_prompt,
    #     use_tool=True,
    #     max_tool_iterations=2
    # )

    # 解析景点数据
    raw_attractions = []
    try:
        # if isinstance(attraction_raw, str):
        #     if "maps_text_search" in attraction_raw:
                result = ToolsManager().call_tool(
                    "maps_text_search",
                    {"keywords": keywords, "city": destination}
                )
                raw_attractions = result.content if result else []
    except Exception as e:
        logger.error(f"❌ [Attraction Worker] 景点搜索失败: {e}")

    if not raw_attractions:
        logger.warning(f"❌ [Attraction Worker] 景点数据为空")
    logger.info(f"✅ [Attraction Worker] 景点搜索完成")


    # 返回单个结果，reducer 会自动合并
    return {
        "completed_tasks": [{
            "task_type": "attraction_search",
            "result": raw_attractions,
        }],
        "raw_attractions": raw_attractions
    }

# ============================================================
# 天气查询工作节点
# ============================================================

async def weather_search_worker(state: WeatherSearchWorkerState) -> Dict[str, Any]:
    """
    天气查询工作节点
    """
    task_input = state.get("task_input")
    destination = task_input["destination"]

    logger.info(f"🔧 [Weather Worker] 开始查询 {destination} 的天气...")

    # 调用 LLM 查询天气
    # weather_prompt = f"请查询 {destination} 的天气"
    # weather_raw = await invoke_llm_with_system(
    #     WEATHER_SEARCH_PROMPT,
    #     weather_prompt,
    #     use_tool=True,
    #     max_tool_iterations=2
    # )

    # 解析天气数据
    raw_weather = []
    try:
        # if isinstance(weather_raw, str):
        #     if "maps_weather" in weather_raw:
                result = ToolsManager().call_tool(
                    "maps_weather",
                    {"city": destination}
                )
                raw_weather = result.content if result else []
    except Exception as e:
        logger.error(f"❌ [Weather Worker] 天气查询失败: {e}")

    logger.info(f"✅ [Weather Worker] 天气查询完成，数量: {len(raw_weather)}")

    # 返回单个结果，reducer 会自动合并
    return {
        "completed_tasks": [{
            "task_type": "weather_search",
            "result": raw_weather,
        }],
        "raw_weather": raw_weather
    }

# ============================================================
# 每日规划工作节点
# ============================================================

async def daily_planning_worker(state: DailyPlanningWorkerState) -> Dict[str, Any]:
    """
    每日规划工作节点
    """
    task_input = state.get("task_input")
    day_num = task_input["day_num"]
    destination = task_input["destination"]
    preferences = task_input.get("preferences", [])
    hotel_preferences = task_input.get("hotel_preferences", [])

    logger.info(f"📅 [Daily Planning Worker] 规划第 {day_num} 天...")

    # 从 task_input 中获取景点和天气信息
    raw_attractions = task_input.get("raw_attractions", [])
    raw_weather = task_input.get("raw_weather", [])

    # 获取预算和日期信息
    budget_level = task_input.get("budget_level", "中等")
    start_date = task_input.get("start_date", datetime.now().strftime("%Y-%m-%d"))

    # 计算当前日期
    current_date = calculate_current_date(start_date, day_num)

    # 获取天气
    today_weather = get_weather_for_date(raw_weather, current_date)
    weather_text = format_weather_to_text(today_weather)

    # 过滤未分配的景点
    assigned_attraction_names = task_input.get("assigned_attraction_names", [])
    available_attractions = filter_unassigned_attractions(raw_attractions, assigned_attraction_names)

    # 景点规划
    attraction_prompt = build_daily_attraction_prompt(
        day_num=day_num,
        destination=destination,
        raw_attractions=available_attractions,
        weather_text=weather_text,
        preferences=preferences,
        budget_level=budget_level,
    )

    attraction_raw = await invoke_llm_with_system(DAILY_ATTRACTION_PLAN_PROMPT, attraction_prompt)
    attractions_data = parse_json_response(attraction_raw) if attraction_raw else []

    # 转换为模型
    attractions = []
    for item in attractions_data:
        attraction = dict_to_attraction(item)
        if attraction:
            attractions.append(attraction)

    # 酒店规划
    attraction_summary = "、".join([a.name for a in attractions]) if attractions else "休息日"
    hotel_prompt = build_daily_hotel_prompt(
        start_date=current_date,
        day_num=day_num,
        destination=destination,
        day_attractions_summary=attraction_summary,
        budget_level=budget_level,
        hotel_preferences=hotel_preferences,
    )

    hotel_raw = await invoke_llm_with_system(DAILY_HOTEL_PLAN_PROMPT, hotel_prompt, use_tool=True, max_tool_iterations=4)
    hotel_data = parse_json_response(hotel_raw) if hotel_raw else {}
    hotel = dict_to_hotel(hotel_data) if hotel_data else None

    # 餐饮规划
    assigned_dining_names = task_input.get("assigned_dining_names", [])
    dining_prompt = build_daily_dining_prompt(
        day_num=day_num,
        destination=destination,
        day_attractions_summary=attraction_summary,
        budget_level=budget_level,
        assigned_dining_names=assigned_dining_names,
    )

    dining_raw = await invoke_llm_with_system(DAILY_DINING_PLAN_PROMPT, dining_prompt, use_tool=True, max_tool_iterations=4)
    dining_data = parse_json_response(dining_raw) if dining_raw else []

    # 转换为模型
    dining = []
    for item in dining_data:
        meal = dict_to_meal(item)
        if meal:
            dining.append(meal)

    # 计算预算
    attractions_dict_list = [a.model_dump() for a in attractions]
    hotel_dict = hotel.model_dump() if hotel else {}
    dining_dict_list = [d.model_dump() for d in dining]
    daily_budget = calculate_daily_budget(attractions_dict_list, hotel_dict, dining_dict_list, budget_level)

    # 组装 DailyPlan
    daily_plan = DailyPlan(
        day=day_num,
        theme="",
        weather=today_weather,
        hotels=[hotel] if hotel else [],
        attractions=attractions,
        dining=dining,
        budget=daily_budget,
    )

    # 验证
    daily_plan = validate_and_filter_daily_plan(daily_plan, destination)

    logger.info(
        f"✅ [Daily Planning Worker] 第 {day_num} 天规划完成: "
        f"{len(attractions)} 个景点, {1 if hotel else 0} 个酒店, {len(dining)} 个餐饮"
    )

    # 返回单个结果，reducer 会自动合并
    return {
        "completed_tasks": [{
            "task_type": "daily_planning",
            "day_num": day_num,
            "result": daily_plan.model_dump(),
            "attraction_summary": attraction_summary,
        }]
    }

# ============================================================
# 合成器节点
# ============================================================

async def synthesizer_node(state: CoordinatorState) -> Dict[str, Any]:
    """
    合成器节点：汇总工作节点的结果并生成最终行程
    """
    logger.info("🤝 [Synthesizer] 开始汇总结果...")

    request = state["request"]
    destination = request["destination"]
    duration = state["duration"]
    budget_level = state.get("budget_level", "中等")

    # 从 completed_tasks 中提取结果
    completed_tasks = state.get("completed_tasks", [])

    logger.info(f"🤝 [Synthesizer] 共有 {len(completed_tasks)} 个完成任务")

    # 分类处理结果
    raw_attractions = []
    raw_weather = []
    daily_plans = []
    daily_summaries = []

    for task in completed_tasks:
        task_type = task.get("task_type")
        result = task.get("result")

        if task_type == "attraction_search" and result:
            raw_attractions = result
            logger.info(f"🤝 [Synthesizer] 找到景点搜索结果: {len(result)} 个")
        elif task_type == "weather_search" and result:
            raw_weather = result
            logger.info(f"🤝 [Synthesizer] 找到天气查询结果: {len(result)} 条")
        elif task_type == "daily_planning" and result:
            daily_plans.append(result)
            daily_summaries.append(task.get("attraction_summary", ""))
            logger.info(f"🤝 [Synthesizer] 找到第 {result.get('day')} 天规划结果")

    # 按天排序
    daily_plans.sort(key=lambda x: x.get("day", 0))

    logger.info(
        f"🤝 [Synthesizer] 汇总完成: "
        f"{len(raw_attractions)} 个景点, {len(raw_weather)} 条天气, {len(daily_plans)} 天行程"
    )

    # 如果没有每日规划结果，返回错误
    if not daily_plans:
        logger.error("❌ [Synthesizer] 没有每日规划结果")
        return {"final_response": None}

    # 生成标题和主题
    theme_prompt = build_theme_prompt(destination, duration, daily_summaries)
    theme_raw = await invoke_llm_with_system(DAILY_THEME_PROMPT, theme_prompt)

    trip_title = f"{destination}{duration}日游"
    daily_themes = []
    try:
        theme_data = parse_json_response(theme_raw) if theme_raw else {}
        trip_title = theme_data.get("trip_title", trip_title)
        daily_themes = theme_data.get("daily_themes", [])
    except Exception as e:
        logger.error(f"❌ [Synthesizer] 标题/主题生成解析失败: {e}")
        daily_themes = [f"第{i+1}天行程" for i in range(duration)]

    # 重建 DailyPlan 并写入主题
    daily_plan_models = []
    for idx, daily_plan_dict in enumerate(daily_plans):
        daily_plan = DailyPlan(**daily_plan_dict)
        daily_plan.theme = daily_themes[idx] if idx < len(daily_themes) else f"第{idx + 1}天行程"
        daily_plan_models.append(daily_plan)

    # 验证相邻天
    validate_adjacent_days(daily_plan_models)

    # 计算总预算
    total_attraction_ticket_cost = sum(day.budget.attraction_ticket_cost for day in daily_plan_models)
    total_hotel_cost = sum(day.budget.hotel_cost for day in daily_plan_models)
    total_dining_cost = sum(day.budget.dining_cost for day in daily_plan_models)
    total_transport_cost = sum(day.budget.transport_cost for day in daily_plan_models)
    total_cost = total_attraction_ticket_cost + total_hotel_cost + total_dining_cost + total_transport_cost

    budget_info = BUDGET_RANGES.get(budget_level, BUDGET_RANGES["中等"])
    total_daily_max = budget_info["daily_total_max"] * duration
    is_total_over_budget = total_cost > total_daily_max

    if is_total_over_budget:
        logger.warning(
            f"⚠️ [Synthesizer] 总预算超标: 实际 {total_cost:.0f}元, "
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
    final_response = {
        "id": state.get("request_id"),
        "trip_title": trip_title,
        "total_budget": total_budget.model_dump(),
        "days": [day.model_dump() for day in daily_plan_models],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    logger.info(f"✅ [Synthesizer] 结果汇总完成，行程标题：{trip_title}")

    return {"final_response": final_response}

# ============================================================
# 条件边函数：检查是否继续
# ============================================================

def should_continue(state: CoordinatorState) -> Literal["synthesizer", "orchestrator"]:
    """
    检查是否需要继续生成任务
    """
    completed_tasks = state.get("completed_tasks", [])
    duration = state.get("duration", 1)

    # 统计已完成的任务
    phase1_completed = sum(1 for t in completed_tasks if t.get("task_type") in ["attraction_search", "weather_search"])
    phase2_completed = sum(1 for t in completed_tasks if t.get("task_type") == "daily_planning")

    logger.info(f"🔍 [Should Continue] 阶段1完成: {phase1_completed}/2, 阶段2完成: {phase2_completed}/{duration}")

    # 如果所有任务完成，进入合成器
    if phase2_completed >= duration:
        return "synthesizer"

    # 否则继续生成任务
    return "orchestrator"

# ============================================================
# 构建协调器-工作器图
# ============================================================

def build_orchestrator_worker_graph() -> StateGraph:
    """
    构建协调器-工作器图
    结构：
        START -> orchestrator -> [Send] -> workers -> should_continue -> orchestrator/synthesizer
    """
    graph = StateGraph(CoordinatorState)

    # 添加节点
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("attraction_search_worker", attraction_search_worker)
    graph.add_node("weather_search_worker", weather_search_worker)
    graph.add_node("daily_planning_worker", daily_planning_worker)
    graph.add_node("synthesizer", synthesizer_node)

    # 添加边
    graph.add_edge(START, "orchestrator")

    # 从 orchestrator 动态分配工作节点
    graph.add_conditional_edges(
        "orchestrator",
        assign_workers,
        ["attraction_search_worker", "weather_search_worker", "daily_planning_worker"]
    )

    # 所有工作节点完成后，检查是否需要继续
    for worker in ["attraction_search_worker", "weather_search_worker", "daily_planning_worker"]:
        graph.add_conditional_edges(
            worker,
            should_continue,
            {
                "orchestrator": "orchestrator",
                "synthesizer": "synthesizer"
            }
        )

    # 合成器完成后结束
    graph.add_edge("synthesizer", END)

    return graph

# ============================================================
# 入口类
# ============================================================

class TripPlannerGraph:
    """
    协调器-工作器旅行规划器
    基于 LangGraph 的 Send API 实现协调器-工作器架构
    """

    def __init__(self):
        """初始化规划器"""
        _load_tools()
        self.graph = build_orchestrator_worker_graph().compile()
        logger.info("✅ [Orchestrator-Worker] 协调器-工作器图构建完成")

    async def plan_trip(
        self,
        request: TripPlanRequest,
        user_id: str
    ) -> Optional[TripPlanResponse]:
        """
        规划行程 - 协调器-工作器模式
        """
        request_id = f"ow_{datetime.now().timestamp()}"

        # 计算行程天数
        start_date = request.start_date
        end_date = request.end_date
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        duration = (end_dt - start_dt).days + 1

        # 初始化状态
        initial_state: CoordinatorState = {
            "request_id": request_id,
            "request": request.model_dump(),
            "user_id": user_id,
            "destination": request.destination,
            "duration": duration,
            "budget_level": request.budget if request.budget else "中等",
            "start_date": start_date,
            "preferences": request.preferences if request.preferences else [],
            "hotel_preferences": request.hotel_preferences if request.hotel_preferences else [],
            "sections": [],  # 行程计划
            "completed_tasks": [],
            "raw_attractions": [],
            "raw_weather": [],
            "final_response": None
        }

        try:
            logger.info(f"🚀 [Orchestrator-Worker] 开始规划行程: {request.destination}")

            # 执行图
            final_state = await self.graph.ainvoke(
                initial_state,
                {"recursion_limit": 50}
            )

            if final_state.get("final_response"):
                return TripPlanResponse(**final_state["final_response"])

            logger.warning(f"⚠️ [Orchestrator-Worker] 行程规划完成但无最终响应")
            return None

        except Exception as e:
            logger.error(
                f"❌ [Orchestrator-Worker] 行程规划失败: {e}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "destination": request.destination
                }
            )
            return None