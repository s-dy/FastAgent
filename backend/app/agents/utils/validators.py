from typing import List

from app.models.trip import DailyPlan
from app.observability.logger import default_logger as logger
from app.agents.utils.geo import validate_location_in_city, calculate_distance

def validate_and_filter_daily_plan(daily_plan: DailyPlan, destination: str) -> DailyPlan:
    """验证并过滤单日行程计划中不在目标城市范围内的景点和餐饮"""
    valid_attractions = []
    for attraction in daily_plan.attractions:
        if attraction.location:
            lat = float(attraction.location.latitude)
            lng = float(attraction.location.longitude)
            if validate_location_in_city(lat, lng, destination):
                valid_attractions.append(attraction)
            else:
                logger.warning(
                    f"移除不在目标城市范围内的景点: {attraction.name} "
                    f"(位置: {lat}, {lng}, 目标城市: {destination})"
                )
        else:
            logger.warning(f"移除没有位置信息的景点: {attraction.name}")

    if len(valid_attractions) > 1:
        for idx in range(len(valid_attractions) - 1):
            att_current = valid_attractions[idx]
            att_next = valid_attractions[idx + 1]
            if att_current.location and att_next.location:
                distance = calculate_distance(
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

    valid_dining = []
    for meal in daily_plan.dining:
        if meal.location:
            lat = float(meal.location.latitude)
            lng = float(meal.location.longitude)
            if validate_location_in_city(lat, lng, destination):
                valid_dining.append(meal)
            else:
                logger.warning(f"移除不在目标城市范围内的餐饮: {meal.name}")
        else:
            valid_dining.append(meal)

    valid_hotels = []
    for hotel in daily_plan.hotels:
        if hotel.location:
            lat = float(hotel.location.latitude)
            lng = float(hotel.location.longitude)
            if validate_location_in_city(lat, lng, destination):
                valid_hotels.append(hotel)
            else:
                logger.warning(f"第{daily_plan.day}天的推荐酒店不在目标城市范围内: {hotel.name}")
        else:
            valid_hotels.append(hotel)

    daily_plan.attractions = valid_attractions
    daily_plan.dining = valid_dining
    daily_plan.hotels = valid_hotels
    return daily_plan

def validate_adjacent_days(daily_plans: List[DailyPlan]) -> None:
    """验证相邻天景点距离"""
    for idx in range(len(daily_plans) - 1):
        day_current = daily_plans[idx]
        day_next = daily_plans[idx + 1]
        if day_current.attractions and day_next.attractions:
            last_attraction = day_current.attractions[-1]
            first_attraction = day_next.attractions[0]
            if last_attraction.location and first_attraction.location:
                distance = calculate_distance(
                    float(last_attraction.location.latitude),
                    float(last_attraction.location.longitude),
                    float(first_attraction.location.latitude),
                    float(first_attraction.location.longitude),
                )
                if distance > 100:
                    logger.warning(
                        f"第{day_current.day}天和第{day_next.day}天的景点距离较远: {distance:.2f}公里"
                    )
