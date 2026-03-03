from typing import List, Dict

from app.models.common import Budget
from app.observability.logger import default_logger as logger
from .geo import calculate_distance

# 预算估算常量（每天每人）
TRANSPORT_COST_PER_DAY = {
    "经济": 30.0,
    "中等": 60.0,
    "适中": 60.0,
    "豪华": 150.0,
}

# 每公里交通费用估算（用于基于距离的动态计算）
TRANSPORT_COST_PER_KM = {
    "经济": 1.5,   # 公交/地铁为主
    "中等": 3.0,   # 打车为主
    "适中": 3.0,
    "豪华": 6.0,   # 专车/包车
}

# 预算等级对应的具体价格范围
BUDGET_RANGES = {
    "经济": {
        "hotel_range": "100-300元/晚",
        "hotel_max": 300,
        "dining_per_meal": "20-50元/人",
        "dining_meal_max": 50,
        "daily_total_max": 500,
        "description": "以经济实惠为主，选择性价比高的选项",
    },
    "中等": {
        "hotel_range": "300-600元/晚",
        "hotel_max": 600,
        "dining_per_meal": "50-100元/人",
        "dining_meal_max": 100,
        "daily_total_max": 1000,
        "description": "兼顾品质与价格，选择舒适但不奢华的选项",
    },
    "适中": {
        "hotel_range": "300-600元/晚",
        "hotel_max": 600,
        "dining_per_meal": "50-100元/人",
        "dining_meal_max": 100,
        "daily_total_max": 1000,
        "description": "兼顾品质与价格，选择舒适但不奢华的选项",
    },
    "豪华": {
        "hotel_range": "600-1500元/晚",
        "hotel_max": 1500,
        "dining_per_meal": "100-300元/人",
        "dining_meal_max": 300,
        "daily_total_max": 2500,
        "description": "追求高品质体验，选择高档酒店和特色餐厅",
    },
}


def estimate_transport_cost_by_distance(attractions_data: List[Dict], budget_level: str) -> float:
    """基于景点间实际距离估算交通费用"""
    valid_locations = []
    for attraction in attractions_data:
        location = attraction.get("location", {})
        if isinstance(location, dict):
            lat = location.get("latitude")
            lng = location.get("longitude")
            if lat is not None and lng is not None:
                try:
                    valid_locations.append((float(lat), float(lng)))
                except (ValueError, TypeError):
                    continue

    if len(valid_locations) < 2:
        return TRANSPORT_COST_PER_DAY.get(budget_level, 60.0)

    total_distance_km = 0.0
    for idx in range(len(valid_locations) - 1):
        lat1, lng1 = valid_locations[idx]
        lat2, lng2 = valid_locations[idx + 1]
        total_distance_km += calculate_distance(lat1, lng1, lat2, lng2)

    cost_per_km = TRANSPORT_COST_PER_KM.get(budget_level, 3.0)
    estimated_cost = total_distance_km * cost_per_km
    minimum_cost = TRANSPORT_COST_PER_DAY.get(budget_level, 60.0) * 0.5
    return max(estimated_cost, minimum_cost)

def calculate_daily_budget(
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

    transport_cost = estimate_transport_cost_by_distance(attractions_data, budget_level)
    total = attraction_ticket_cost + hotel_cost + dining_cost + transport_cost

    budget_info = BUDGET_RANGES.get(budget_level, BUDGET_RANGES["中等"])
    is_over_budget = total > budget_info["daily_total_max"]

    return Budget(
        attraction_ticket_cost=attraction_ticket_cost,
        hotel_cost=hotel_cost,
        dining_cost=dining_cost,
        transport_cost=transport_cost,
        total=total,
        budget_level=budget_level,
        is_over_budget=is_over_budget,
    )

def check_budget_compliance(daily_budget: Budget, budget_level: str, day_num: int) -> None:
    """检查单日预算是否超标，超标时记录告警日志"""
    budget_info = BUDGET_RANGES.get(budget_level, BUDGET_RANGES["中等"])
    daily_max = budget_info["daily_total_max"]
    warning_threshold = daily_max * 1.5

    if daily_budget.total > warning_threshold:
        logger.warning(
            f"⚠️ 第{day_num}天预算严重超标: 实际 {daily_budget.total:.0f}元, "
            f"预算等级「{budget_level}」每日上限 {daily_max}元 (告警阈值 {warning_threshold:.0f}元)"
        )
    elif daily_budget.total > daily_max:
        logger.warning(
            f"⚠️ 第{day_num}天预算超标: 实际 {daily_budget.total:.0f}元, "
            f"预算等级「{budget_level}」每日上限 {daily_max}元"
        )

    hotel_max = budget_info["hotel_max"]
    if daily_budget.hotel_cost > hotel_max:
        logger.warning(
            f"⚠️ 第{day_num}天酒店费用超标: 实际 {daily_budget.hotel_cost:.0f}元/晚, "
            f"预算等级「{budget_level}」酒店上限 {hotel_max}元/晚"
        )

    dining_meal_max = budget_info["dining_meal_max"]
    if daily_budget.dining_cost > dining_meal_max * 4:
        logger.warning(
            f"⚠️ 第{day_num}天餐饮总费用偏高: 实际 {daily_budget.dining_cost:.0f}元, "
            f"预算等级「{budget_level}」单餐上限 {dining_meal_max}元/人"
        )
