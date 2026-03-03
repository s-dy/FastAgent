from typing import Optional, Dict

from app.models.common import Location, Attraction, Meal, Hotel
from app.observability.logger import default_logger as logger

def dict_to_attraction(data: Dict) -> Optional[Attraction]:
    """将字典转换为 Attraction 模型"""
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

def dict_to_hotel(data: Dict) -> Optional[Hotel]:
    """将字典转换为 Hotel 模型"""
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

def dict_to_meal(data: Dict) -> Optional[Meal]:
    """将字典转换为 Meal 模型"""
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
