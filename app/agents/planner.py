import json
import math
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any

from fastagent.core import LLMClient
from fastagent.agents import MessageState
from fastagent.tools import ToolRegistry
from fastagent.tools.builtin import MCPTool
from fastagent.memory import MemoryConfig, MemoryManager

from app.models.common import Location, Attraction, Meal, Hotel, Budget
from app.models.trip import TripPlanRequest, TripPlanResponse, DailyPlan
from app.observability.logger import default_logger as logger
from app.config import settings
from app.services.context_manager import ContextManager, get_context_manager
from app.agents.agents import (
    AttractionSearchAgent,
    WeatherQueryAgent,
    DailyAttractionPlanAgent,
    DailyHotelPlanAgent,
    DailyDiningPlanAgent,
    TripThemeAgent,
)
from app.observability.logger import get_request_id

# 主要城市的经纬度范围（用于验证）
CITY_BOUNDS = {
    "北京": {"lat_min": 39.4, "lat_max": 41.1, "lng_min": 115.7, "lng_max": 117.4},
    "上海": {"lat_min": 30.7, "lat_max": 31.9, "lng_min": 120.8, "lng_max": 122.2},
    "广州": {"lat_min": 22.7, "lat_max": 23.8, "lng_min": 112.9, "lng_max": 114.0},
    "深圳": {"lat_min": 22.4, "lat_max": 22.9, "lng_min": 113.7, "lng_max": 114.6},
    "成都": {"lat_min": 30.4, "lat_max": 30.9, "lng_min": 103.9, "lng_max": 104.5},
    "杭州": {"lat_min": 30.0, "lat_max": 30.5, "lng_min": 119.5, "lng_max": 120.5},
    "重庆": {"lat_min": 29.3, "lat_max": 29.9, "lng_min": 106.2, "lng_max": 106.8},
    "武汉": {"lat_min": 30.3, "lat_max": 31.0, "lng_min": 113.9, "lng_max": 114.6},
    "西安": {"lat_min": 34.0, "lat_max": 34.5, "lng_min": 108.7, "lng_max": 109.2},
    "苏州": {"lat_min": 31.1, "lat_max": 31.5, "lng_min": 120.3, "lng_max": 121.0},
    "天津": {"lat_min": 38.9, "lat_max": 39.6, "lng_min": 116.9, "lng_max": 117.9},
    "南京": {"lat_min": 31.9, "lat_max": 32.2, "lng_min": 118.4, "lng_max": 119.2},
    "长沙": {"lat_min": 28.1, "lat_max": 28.4, "lng_min": 112.8, "lng_max": 113.2},
    "郑州": {"lat_min": 34.4, "lat_max": 34.9, "lng_min": 113.4, "lng_max": 113.9},
    "厦门": {"lat_min": 24.4, "lat_max": 24.6, "lng_min": 118.0, "lng_max": 118.2},
    "青岛": {"lat_min": 35.9, "lat_max": 36.4, "lng_min": 119.9, "lng_max": 120.7},
    "大连": {"lat_min": 38.7, "lat_max": 39.2, "lng_min": 121.3, "lng_max": 122.0},
    "三亚": {"lat_min": 18.1, "lat_max": 18.4, "lng_min": 109.3, "lng_max": 109.7},
    "丽江": {"lat_min": 26.8, "lat_max": 27.2, "lng_min": 100.1, "lng_max": 100.5},
    "桂林": {"lat_min": 25.1, "lat_max": 25.5, "lng_min": 110.1, "lng_max": 110.6},
    "昆明": {"lat_min": 24.7, "lat_max": 25.3, "lng_min": 102.5, "lng_max": 103.1},
    "哈尔滨": {"lat_min": 45.5, "lat_max": 46.0, "lng_min": 126.4, "lng_max": 127.1},
    "沈阳": {"lat_min": 41.5, "lat_max": 42.0, "lng_min": 123.2, "lng_max": 123.8},
    "济南": {"lat_min": 36.5, "lat_max": 36.8, "lng_min": 116.8, "lng_max": 117.3},
    "黄山": {"lat_min": 29.8, "lat_max": 30.2, "lng_min": 118.1, "lng_max": 118.5},
    "张家界": {"lat_min": 28.9, "lat_max": 29.3, "lng_min": 110.2, "lng_max": 110.7},
    "敦煌": {"lat_min": 39.8, "lat_max": 40.3, "lng_min": 94.4, "lng_max": 95.1},
    "拉萨": {"lat_min": 29.5, "lat_max": 30.0, "lng_min": 90.9, "lng_max": 91.5},
    "乌鲁木齐": {"lat_min": 43.7, "lat_max": 44.2, "lng_min": 87.4, "lng_max": 88.0},
    "宁波": {"lat_min": 29.8, "lat_max": 30.0, "lng_min": 121.3, "lng_max": 121.8},
}

# 预算估算常量（每天每人）
TRANSPORT_COST_PER_DAY = {
    "经济": 30.0,
    "中等": 60.0,
    "适中": 60.0,
    "豪华": 150.0,
}


class PlannerAgent:
    """
    行程规划协调器
    负责协调多个专业智能体，按天分步生成行程计划。
    """

    def __init__(self, llm_service: LLMClient, memory_manager: MemoryManager):
        self.llm = llm_service
        self.settings = settings
        self.memory_manager = memory_manager

        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(MCPTool(
            name="amap",
            description="高德地图服务",
            server_command=f"https://mcp.amap.com/mcp?key={os.getenv('AMAP_MCP_KEY')}",
        ))

    # ============================================================
    # 地理位置验证工具方法
    # ============================================================

    def _validate_location_in_city(self, lat: float, lng: float, city: str) -> bool:
        """验证位置是否在指定城市范围内"""
        if city not in CITY_BOUNDS:
            logger.warning(
                f"⚠️ 城市 '{city}' 不在支持的城市范围内。"
                f"目前支持的城市包括：{', '.join(list(CITY_BOUNDS.keys())[:10])} 等30个热门旅游城市。"
            )
            return False

        bounds = CITY_BOUNDS[city]
        is_valid = (
            bounds["lat_min"] <= lat <= bounds["lat_max"]
            and bounds["lng_min"] <= lng <= bounds["lng_max"]
        )

        if not is_valid:
            logger.warning(
                f"⚠️ 位置 ({lat}, {lng}) 不在城市 '{city}' 的合理范围内，该景点可能不属于目标城市"
            )

        return is_valid

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """使用 Haversine 公式计算两点之间的距离（公里）"""
        earth_radius_km = 6371
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        haversine = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(delta_lng / 2) ** 2
        )
        central_angle = 2 * math.asin(math.sqrt(haversine))
        return earth_radius_km * central_angle

    # ============================================================
    # JSON 解析工具方法
    # ============================================================

    def _parse_json_response(self, raw_text: str) -> Any:
        """
        安全解析 LLM 返回的 JSON 文本。
        自动处理 Markdown 代码块包裹的情况。
        """
        text = raw_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)

    # ============================================================
    # Phase1: 搜索查询构建
    # ============================================================

    def _build_attraction_query(self, request: TripPlanRequest) -> str:
        """构建景点搜索查询"""
        keywords = request.preferences[0] if request.preferences else "景点"
        return f"请使用amap_maps_text_search工具搜索{request.destination}的{keywords}相关景点。"

    def _build_weather_query(self, request: TripPlanRequest) -> str:
        """构建天气搜索查询"""
        return f"请查询{request.destination}的天气信息，日期范围：{request.start_date} 到 {request.end_date}"

    # ============================================================
    # Phase2: 按天规划 - 构建单天 Agent 的 Prompt
    # ============================================================

    def _build_daily_attraction_prompt(
        self,
        day_num: int,
        destination: str,
        raw_attractions: str,
        assigned_attraction_names: List[str],
        weather_text: str,
        preferences: List[str],
    ) -> str:
        """构建单日景点规划的 prompt"""
        assigned_str = "、".join(assigned_attraction_names) if assigned_attraction_names else "无"
        pref_str = "、".join(preferences) if preferences else "无特殊偏好"
        return (
            f"请为前往 {destination} 旅行的第 {day_num} 天规划景点。\n\n"
            f"**用户偏好：** {pref_str}\n"
            f"**当天天气：** {weather_text}\n"
            f"**已在其他天分配的景点（不要重复推荐）：** {assigned_str}\n\n"
            f"**候选景点列表（从以下景点中挑选）：**\n{raw_attractions}\n\n"
            f"请严格按照系统提示中的 JSON 格式输出。"
        )

    def _build_daily_hotel_prompt(
        self,
        day_num: int,
        destination: str,
        day_attractions_summary: str,
        budget_level: str,
        hotel_preferences: List[str],
    ) -> str:
        """构建单日酒店规划的 prompt（Agent 将动态搜索附近酒店）"""
        hotel_pref_str = "、".join(hotel_preferences) if hotel_preferences else "无特殊偏好"
        return (
            f"请为前往 {destination} 旅行的第 {day_num} 天搜索并推荐酒店。\n\n"
            f"**预算水平：** {budget_level}\n"
            f"**酒店偏好：** {hotel_pref_str}\n"
            f"**当天景点位置参考：** {day_attractions_summary}\n\n"
            f"请根据以上景点位置，使用工具搜索这些景点附近的酒店，然后从搜索结果中挑选最合适的一家。\n"
            f"搜索完成后，请严格按照系统提示中的 JSON 格式输出。"
        )

    def _build_daily_dining_prompt(
        self,
        day_num: int,
        destination: str,
        day_attractions_summary: str,
        budget_level: str,
        assigned_dining_names: List[str],
    ) -> str:
        """构建单日餐饮规划的 prompt"""
        assigned_str = "、".join(assigned_dining_names) if assigned_dining_names else "无"
        return (
            f"请为前往 {destination} 旅行的第 {day_num} 天推荐餐饮。\n\n"
            f"**目的地：** {destination}\n"
            f"**预算水平：** {budget_level}\n"
            f"**当天景点位置参考：** {day_attractions_summary}\n"
            f"**已在其他天推荐过的餐厅（不要重复）：** {assigned_str}\n\n"
            f"请严格按照系统提示中的 JSON 格式输出。"
        )

    def _build_theme_prompt(
        self,
        destination: str,
        duration: int,
        daily_summaries: List[str],
    ) -> str:
        """构建行程标题与主题生成的 prompt"""
        summaries_text = ""
        for idx, summary in enumerate(daily_summaries, 1):
            summaries_text += f"第{idx}天：{summary}\n"
        return (
            f"请为前往 {destination} 的 {duration} 天旅行生成标题和每天主题。\n\n"
            f"**每天行程概要：**\n{summaries_text}\n"
            f"请严格按照系统提示中的 JSON 格式输出。"
        )

    # ============================================================
    # Phase2: 单天规划执行
    # ============================================================

    def _plan_single_day(
        self,
        day_num: int,
        request: TripPlanRequest,
        context_manager: ContextManager,
        raw_attractions: str,
        weather_text: str,
        assigned_attraction_names: List[str],
        assigned_dining_names: List[str],
    ) -> Dict[str, Any]:
        """
        为单天调用景点、酒店、餐饮三个规划 Agent，返回解析后的结构化数据。
        景点先行（酒店和餐饮依赖景点位置），然后酒店和餐饮并行。

        Returns:
            包含 attractions, hotel, dining 三个键的字典
        """
        # 构建景点 prompt
        attraction_prompt = self._build_daily_attraction_prompt(
            day_num=day_num,
            destination=request.destination,
            raw_attractions=raw_attractions,
            assigned_attraction_names=assigned_attraction_names,
            weather_text=weather_text,
            preferences=request.preferences or [],
        )

        # 先执行景点规划（因为酒店和餐饮依赖景点位置）
        attraction_agent = DailyAttractionPlanAgent(
            llm=self.llm,
            state=MessageState(),
            context_manager=context_manager,
            memory_manager=self.memory_manager,
        )
        attraction_raw = attraction_agent.run(attraction_prompt)

        # 解析景点结果
        try:
            attractions_data = self._parse_json_response(attraction_raw)
            if not isinstance(attractions_data, list):
                attractions_data = [attractions_data]
        except (json.JSONDecodeError, Exception) as parse_error:
            logger.error(f"❌ 第{day_num}天景点规划 JSON 解析失败: {parse_error}")
            attractions_data = []

        # 构建景点摘要（供酒店和餐饮 Agent 参考位置）
        attraction_names_for_summary = []
        for attraction in attractions_data:
            name = attraction.get("name", "未知景点")
            location = attraction.get("location", {})
            attraction_names_for_summary.append(
                f"{name}(经度:{location.get('longitude', '?')}, 纬度:{location.get('latitude', '?')})"
            )
        day_attractions_summary = "、".join(attraction_names_for_summary) if attraction_names_for_summary else "暂无景点信息"

        # 构建酒店和餐饮 prompt（酒店不再需要 raw_hotels，Agent 会动态搜索）
        hotel_prompt = self._build_daily_hotel_prompt(
            day_num=day_num,
            destination=request.destination,
            day_attractions_summary=day_attractions_summary,
            budget_level=request.budget,
            hotel_preferences=request.hotel_preferences or [],
        )
        dining_prompt = self._build_daily_dining_prompt(
            day_num=day_num,
            destination=request.destination,
            day_attractions_summary=day_attractions_summary,
            budget_level=request.budget,
            assigned_dining_names=assigned_dining_names,
        )

        # 并行执行酒店（动态搜索+规划）和餐饮规划
        hotel_agent = DailyHotelPlanAgent(
            llm=self.llm,
            state=MessageState(),
            tool_registry=self.tool_registry,
            context_manager=context_manager,
            memory_manager=self.memory_manager,
        )
        dining_agent = DailyDiningPlanAgent(
            llm=self.llm,
            state=MessageState(),
            context_manager=context_manager,
            memory_manager=self.memory_manager,
        )

        hotel_data = {}
        dining_data = []

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"day{day_num}_plan") as executor:
            future_hotel = executor.submit(hotel_agent.run, hotel_prompt)
            future_dining = executor.submit(dining_agent.run, dining_prompt)

            try:
                hotel_raw = future_hotel.result(timeout=120)
                hotel_data = self._parse_json_response(hotel_raw)
                if isinstance(hotel_data, list):
                    hotel_data = hotel_data[0] if hotel_data else {}
            except (json.JSONDecodeError, Exception) as parse_error:
                logger.error(f"❌ 第{day_num}天酒店规划解析失败: {parse_error}")

            try:
                dining_raw = future_dining.result(timeout=120)
                dining_data = self._parse_json_response(dining_raw)
                if not isinstance(dining_data, list):
                    dining_data = [dining_data]
            except (json.JSONDecodeError, Exception) as parse_error:
                logger.error(f"❌ 第{day_num}天餐饮规划解析失败: {parse_error}")

        return {
            "attractions": attractions_data,
            "hotel": hotel_data,
            "dining": dining_data,
        }

    # ============================================================
    # Phase3: 预算计算
    # ============================================================

    def _calculate_daily_budget(
        self,
        attractions_data: List[Dict],
        hotel_data: Dict,
        dining_data: List[Dict],
        budget_level: str,
    ) -> Budget:
        """根据各 Agent 输出的结构化数据，程序化计算单日预算"""
        attraction_ticket_cost = 0.0
        for attraction in attractions_data:
            ticket_price = attraction.get("ticket_price", 0)
            if isinstance(ticket_price, str):
                try:
                    ticket_price = int(ticket_price)
                except ValueError:
                    ticket_price = 0
            attraction_ticket_cost += float(ticket_price)

        hotel_cost = 0.0
        estimated_hotel = hotel_data.get("estimated_cost", 0)
        if isinstance(estimated_hotel, str):
            try:
                estimated_hotel = int(estimated_hotel)
            except ValueError:
                estimated_hotel = 0
        hotel_cost = float(estimated_hotel)

        dining_cost = 0.0
        for meal in dining_data:
            meal_cost = meal.get("estimated_cost", 0)
            if isinstance(meal_cost, str):
                try:
                    meal_cost = int(meal_cost)
                except ValueError:
                    meal_cost = 0
            dining_cost += float(meal_cost)

        transport_cost = TRANSPORT_COST_PER_DAY.get(budget_level, 60.0)

        total = attraction_ticket_cost + hotel_cost + dining_cost + transport_cost

        return Budget(
            attraction_ticket_cost=attraction_ticket_cost,
            hotel_cost=hotel_cost,
            dining_cost=dining_cost,
            transport_cost=transport_cost,
            total=total,
        )

    # ============================================================
    # Phase3: 数据转换 - 将 Agent 输出的 dict 转为 Pydantic 模型
    # ============================================================

    def _dict_to_attraction(self, data: Dict) -> Optional[Attraction]:
        """将字典转换为 Attraction 模型，转换失败返回 None"""
        try:
            location_data = data.get("location", {})
            location = Location(
                longitude=float(location_data.get("longitude", 0)),
                latitude=float(location_data.get("latitude", 0)),
            )

            visit_duration = data.get("visit_duration", 120)
            if isinstance(visit_duration, str):
                try:
                    visit_duration = int(visit_duration)
                except ValueError:
                    visit_duration = 120

            rating = data.get("rating")
            if rating is not None:
                try:
                    rating = float(rating)
                except (ValueError, TypeError):
                    rating = None

            ticket_price = data.get("ticket_price", 0)
            if isinstance(ticket_price, str):
                try:
                    ticket_price = int(ticket_price)
                except ValueError:
                    ticket_price = 0

            return Attraction(
                name=data.get("name", "未知景点"),
                address=data.get("address", ""),
                location=location,
                visit_duration=visit_duration,
                description=data.get("description", ""),
                category=data.get("category", "景点"),
                rating=rating,
                image_url=data.get("image_url"),
                ticket_price=ticket_price,
            )
        except Exception as conversion_error:
            logger.error(f"景点数据转换失败: {conversion_error}, 原始数据: {data}")
            return None

    def _dict_to_hotel(self, data: Dict) -> Optional[Hotel]:
        """将字典转换为 Hotel 模型，转换失败返回 None"""
        try:
            location = None
            location_data = data.get("location")
            if location_data and isinstance(location_data, dict):
                location = Location(
                    longitude=float(location_data.get("longitude", 0)),
                    latitude=float(location_data.get("latitude", 0)),
                )

            estimated_cost = data.get("estimated_cost", 0)
            if isinstance(estimated_cost, str):
                try:
                    estimated_cost = int(estimated_cost)
                except ValueError:
                    estimated_cost = 0

            return Hotel(
                name=data.get("name", "未知酒店"),
                address=data.get("address", ""),
                location=location,
                price_range=str(data.get("price_range", "")),
                rating=str(data.get("rating", "")),
                distance=str(data.get("distance", "")),
                type=str(data.get("type", "")),
                estimated_cost=estimated_cost,
            )
        except Exception as conversion_error:
            logger.error(f"酒店数据转换失败: {conversion_error}, 原始数据: {data}")
            return None

    def _dict_to_meal(self, data: Dict) -> Optional[Meal]:
        """将字典转换为 Meal 模型，转换失败返回 None"""
        try:
            location = None
            location_data = data.get("location")
            if location_data and isinstance(location_data, dict):
                location = Location(
                    longitude=float(location_data.get("longitude", 0)),
                    latitude=float(location_data.get("latitude", 0)),
                )

            estimated_cost = data.get("estimated_cost", 0)
            if isinstance(estimated_cost, str):
                try:
                    estimated_cost = int(estimated_cost)
                except ValueError:
                    estimated_cost = 0

            return Meal(
                type=data.get("type", "lunch"),
                name=data.get("name", "未知餐厅"),
                address=data.get("address"),
                location=location,
                description=data.get("description"),
                estimated_cost=estimated_cost,
            )
        except Exception as conversion_error:
            logger.error(f"餐饮数据转换失败: {conversion_error}, 原始数据: {data}")
            return None

    # ============================================================
    # Phase3: 验证和过滤
    # ============================================================

    def _validate_and_filter_daily_plan(self, daily_plan: DailyPlan, destination: str) -> DailyPlan:
        """验证并过滤单日行程计划中不在目标城市范围内的景点和餐饮"""
        # 过滤景点
        valid_attractions = []
        for attraction in daily_plan.attractions:
            if attraction.location:
                lat = float(attraction.location.latitude)
                lng = float(attraction.location.longitude)
                if self._validate_location_in_city(lat, lng, destination):
                    valid_attractions.append(attraction)
                else:
                    logger.warning(
                        f"移除不在目标城市范围内的景点: {attraction.name} "
                        f"(位置: {lat}, {lng}, 目标城市: {destination})"
                    )
            else:
                logger.warning(f"移除没有位置信息的景点: {attraction.name}")

        # 验证同一天景点距离
        if len(valid_attractions) > 1:
            for idx in range(len(valid_attractions) - 1):
                att_current = valid_attractions[idx]
                att_next = valid_attractions[idx + 1]
                if att_current.location and att_next.location:
                    distance = self._calculate_distance(
                        float(att_current.location.latitude),
                        float(att_current.location.longitude),
                        float(att_next.location.latitude),
                        float(att_next.location.longitude),
                    )
                    if distance > 50:
                        logger.warning(
                            f"第{daily_plan.day}天的景点 {att_current.name} 和 {att_next.name} "
                            f"距离较远: {distance:.2f}公里"
                        )

        # 过滤餐饮
        valid_dining = []
        for meal in daily_plan.dining:
            if meal.location:
                lat = float(meal.location.latitude)
                lng = float(meal.location.longitude)
                if self._validate_location_in_city(lat, lng, destination):
                    valid_dining.append(meal)
                else:
                    logger.warning(f"移除不在目标城市范围内的餐饮: {meal.name}")
            else:
                valid_dining.append(meal)

        # 验证酒店
        valid_hotels = []
        for hotel in daily_plan.hotels:
            if hotel.location:
                lat = float(hotel.location.latitude)
                lng = float(hotel.location.longitude)
                if self._validate_location_in_city(lat, lng, destination):
                    valid_hotels.append(hotel)
                else:
                    logger.warning(f"第{daily_plan.day}天的推荐酒店不在目标城市范围内: {hotel.name}")
            else:
                valid_hotels.append(hotel)

        daily_plan.attractions = valid_attractions
        daily_plan.dining = valid_dining
        daily_plan.hotels = valid_hotels
        return daily_plan

    def _validate_adjacent_days(self, daily_plans: List[DailyPlan]):
        """验证相邻天景点距离"""
        for idx in range(len(daily_plans) - 1):
            day_current = daily_plans[idx]
            day_next = daily_plans[idx + 1]

            if day_current.attractions and day_next.attractions:
                last_attraction = day_current.attractions[-1]
                first_attraction = day_next.attractions[0]

                if last_attraction.location and first_attraction.location:
                    distance = self._calculate_distance(
                        float(last_attraction.location.latitude),
                        float(last_attraction.location.longitude),
                        float(first_attraction.location.latitude),
                        float(first_attraction.location.longitude),
                    )
                    if distance > 100:
                        logger.warning(
                            f"第{day_current.day}天和第{day_next.day}天的景点距离较远: {distance:.2f}公里"
                        )

    # ============================================================
    # 主流程: plan_trip
    # ============================================================

    def plan_trip(
        self,
        request: TripPlanRequest,
        user_id: str,
    ) -> Optional[TripPlanResponse]:
        """
        规划行程 - 三阶段流程

        Phase1: 并行搜索原始数据（景点、酒店、天气）
        Phase2: 按天循环，每天并行调用规划 Agent 生成结构化数据
        Phase3: 程序化计算预算 → 生成标题/主题 → 验证 → 拼装

        Args:
            request: 行程规划请求
            user_id: 用户ID

        Returns:
            行程规划响应，失败返回 None
        """
        request_id = get_request_id() or f"req_{datetime.now().timestamp()}"
        context_manager = get_context_manager(request_id)

        # 在上下文中存储请求信息
        context_manager.share_data("request", {
            "destination": request.destination,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "preferences": request.preferences,
            "hotel_preferences": request.hotel_preferences,
            "budget": request.budget,
        })

        # 计算行程天数
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        duration = (end_date - start_date).days + 1

        # 检索用户记忆
        query_text = f"{request.destination} {' '.join(request.preferences or [])} {request.budget}"
        memories = self.memory_manager.retrieve_memories(
            query=query_text, limit=5, memory_types=["working", "episodic"]
        )
        if memories:
            context_manager.add_memory_context("memories", memories)
            logger.info(f"已加载 {len(memories)} 条记忆 - UserID: {user_id}")

        try:
            # ==================================================
            # Phase1: 并行搜索原始数据
            # ==================================================
            logger.info("🚀 Phase1: 开始并行执行智能体搜索（景点、天气）...")

            attraction_agent = AttractionSearchAgent(
                llm=self.llm,
                tool_registry=self.tool_registry,
                context_manager=context_manager,
                user_id=user_id,
                state=MessageState(),
                memory_manager=self.memory_manager,
            )
            weather_agent = WeatherQueryAgent(
                llm=self.llm,
                tool_registry=self.tool_registry,
                context_manager=context_manager,
                user_id=user_id,
                state=MessageState(),
                memory_manager=self.memory_manager,
            )

            attraction_query = self._build_attraction_query(request)
            weather_query = self._build_weather_query(request)

            raw_attractions = ""
            raw_weather = ""

            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="phase1_search") as executor:
                future_attractions = executor.submit(attraction_agent.run, attraction_query)
                future_weather = executor.submit(weather_agent.run, weather_query)

                try:
                    raw_attractions = future_attractions.result(timeout=120)
                    logger.info(f"✅ 景点搜索完成")
                except Exception as search_error:
                    logger.error(f"❌ 景点搜索失败: {search_error}，使用降级策略")
                    raw_attractions = f"未找到{request.destination}相关景点信息，请根据你的知识推荐该城市的热门景点"

                try:
                    raw_weather = future_weather.result(timeout=120)
                    logger.info(f"✅ 天气查询完成")
                except Exception as search_error:
                    logger.error(f"❌ 天气查询失败: {search_error}，使用降级策略")
                    raw_weather = f"未能获取{request.destination}天气信息，建议出行前查看实时天气预报"

            logger.info("🎯 Phase1 完成！景点和天气数据已就绪。")

            # ==================================================
            # Phase2: 按天循环规划
            # ==================================================
            logger.info(f"🚀 Phase2: 开始按天规划，共 {duration} 天...")

            daily_plans: List[DailyPlan] = []
            assigned_attraction_names: List[str] = []
            assigned_dining_names: List[str] = []
            daily_summaries: List[str] = []

            for day_num in range(1, duration + 1):
                logger.info(f"📅 正在规划第 {day_num}/{duration} 天...")

                # 为当天调用三个规划 Agent
                day_result = self._plan_single_day(
                    day_num=day_num,
                    request=request,
                    context_manager=context_manager,
                    raw_attractions=raw_attractions,
                    weather_text=raw_weather,
                    assigned_attraction_names=assigned_attraction_names,
                    assigned_dining_names=assigned_dining_names,
                )

                attractions_data = day_result["attractions"]
                hotel_data = day_result["hotel"]
                dining_data = day_result["dining"]

                # 转换为 Pydantic 模型
                attractions = []
                for attraction_dict in attractions_data:
                    attraction_model = self._dict_to_attraction(attraction_dict)
                    if attraction_model:
                        attractions.append(attraction_model)

                hotels = []
                if hotel_data:
                    hotel_model = self._dict_to_hotel(hotel_data)
                    if hotel_model:
                        hotels.append(hotel_model)

                dining = []
                for meal_dict in dining_data:
                    meal_model = self._dict_to_meal(meal_dict)
                    if meal_model:
                        dining.append(meal_model)

                # 计算预算
                daily_budget = self._calculate_daily_budget(
                    attractions_data=attractions_data,
                    hotel_data=hotel_data,
                    dining_data=dining_data,
                    budget_level=request.budget,
                )

                # 组装 DailyPlan
                daily_plan = DailyPlan(
                    day=day_num,
                    theme="",
                    weather=None,
                    hotels=hotels,
                    attractions=attractions,
                    dining=dining,
                    budget=daily_budget,
                )

                # 验证地理位置
                daily_plan = self._validate_and_filter_daily_plan(daily_plan, request.destination)

                daily_plans.append(daily_plan)

                # 更新已分配列表
                for attraction in daily_plan.attractions:
                    assigned_attraction_names.append(attraction.name)
                for meal in daily_plan.dining:
                    assigned_dining_names.append(meal.name)

                # 生成当天摘要（供主题 Agent 使用）
                attraction_names = [a.name for a in daily_plan.attractions]
                daily_summaries.append("、".join(attraction_names) if attraction_names else "休息日")

                logger.info(f"✅ 第 {day_num} 天规划完成: {len(daily_plan.attractions)} 个景点, "
                            f"{len(daily_plan.hotels)} 个酒店, {len(daily_plan.dining)} 个餐饮")

            # 验证相邻天景点距离
            self._validate_adjacent_days(daily_plans)

            logger.info("🎯 Phase2 完成！所有天数规划已就绪。")

            # ==================================================
            # Phase3: 生成标题/主题 + 计算总预算 + 拼装
            # ==================================================
            logger.info("🚀 Phase3: 生成标题和主题...")

            # 生成行程标题和每天主题
            theme_agent = TripThemeAgent(
                llm=self.llm,
                state=MessageState(),
                context_manager=context_manager,
                memory_manager=self.memory_manager,
            )
            theme_prompt = self._build_theme_prompt(
                destination=request.destination,
                duration=duration,
                daily_summaries=daily_summaries,
            )
            theme_raw = theme_agent.run(theme_prompt)

            trip_title = f"{request.destination}{duration}日游"
            daily_themes = []
            try:
                theme_data = self._parse_json_response(theme_raw)
                trip_title = theme_data.get("trip_title", trip_title)
                daily_themes = theme_data.get("daily_themes", [])
            except (json.JSONDecodeError, Exception) as theme_error:
                logger.error(f"❌ 标题/主题生成解析失败: {theme_error}，使用默认标题")

            # 将主题写入每天的 DailyPlan
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
            total_budget = Budget(
                attraction_ticket_cost=total_attraction_ticket_cost,
                hotel_cost=total_hotel_cost,
                dining_cost=total_dining_cost,
                transport_cost=total_transport_cost,
                total=total_attraction_ticket_cost + total_hotel_cost + total_dining_cost + total_transport_cost,
            )

            # 拼装最终响应
            validated_plan = TripPlanResponse(
                id=request_id,
                trip_title=trip_title,
                total_budget=total_budget,
                days=daily_plans,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            # 存储用户偏好记忆
            self.memory_manager.add_memory(
                memory_type="episodic",
                content=json.dumps({
                    "destination": request.destination,
                    "preferences": request.preferences,
                    "hotel_preferences": request.hotel_preferences,
                    "budget": request.budget,
                    "trip_title": validated_plan.trip_title,
                }),
            )

            logger.info(f"🎉 成功生成行程计划: {validated_plan.trip_title}")
            return validated_plan

        except Exception as planning_error:
            logger.error(
                f"行程规划失败: {planning_error}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "destination": request.destination,
                },
            )
            return None
