import math
from app.observability.logger import default_logger as logger

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

def validate_location_in_city(lat: float, lng: float, city: str) -> bool:
    """验证位置是否在指定城市范围内"""
    if city not in CITY_BOUNDS:
        logger.warning(f"⚠️ 城市 '{city}' 不在支持的城市范围内。")
        return False
    bounds = CITY_BOUNDS[city]
    is_valid = (
        bounds["lat_min"] <= lat <= bounds["lat_max"]
        and bounds["lng_min"] <= lng <= bounds["lng_max"]
    )
    if not is_valid:
        logger.warning(f"⚠️ 位置 ({lat}, {lng}) 不在城市 '{city}' 的合理范围内")
    return is_valid

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
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
