# 问题：LLM 幻觉导致推荐的景点不在目标城市

## 问题描述

LLM 在生成景点推荐时，有时会"幻觉"出不存在的景点，或者推荐不在目标城市范围内的景点。例如，用户规划"杭州"行程，LLM 可能推荐"上海外滩"或者一个坐标在南京的虚构景点。

## 问题现象

1. **跨城市推荐**：规划杭州行程时推荐上海、南京的景点
2. **坐标偏移**：景点名称正确但坐标错误，如"西湖"的坐标指向了千里之外
3. **虚构景点**：推荐不存在的景点，名称看似合理但实际查无此地
4. **同一天景点距离过远**：同一天安排的景点之间距离超过 50km，实际无法在一天内游览

## 影响范围

- 用户看到的行程中包含不合理的景点安排
- 地图上的标记点分散在不同城市，用户体验极差
- 预算计算因景点数据不准确而失真

## 解决方案

### 1. 城市边界数据库

在 `planner.py` 中内置了 30+ 城市的经纬度边界数据：

```python
CITY_BOUNDS = {
    "北京": {"lat_min": 39.4, "lat_max": 41.1, "lng_min": 115.4, "lng_max": 117.5},
    "上海": {"lat_min": 30.7, "lat_max": 31.9, "lng_min": 120.8, "lng_max": 122.2},
    "杭州": {"lat_min": 29.2, "lat_max": 30.6, "lng_min": 118.3, "lng_max": 120.8},
    "成都": {"lat_min": 30.1, "lat_max": 31.4, "lng_min": 103.0, "lng_max": 104.9},
    # ... 30+ 城市
}
```

### 2. 地理位置验证方法

```python
def _validate_location_in_city(self, lat: float, lng: float, city: str) -> bool:
    """验证坐标是否在目标城市范围内"""
    bounds = CITY_BOUNDS.get(city)
    if not bounds:
        return True  # 未知城市不做验证
    
    return (bounds["lat_min"] <= lat <= bounds["lat_max"] and
            bounds["lng_min"] <= lng <= bounds["lng_max"])
```

### 3. Haversine 距离计算

```python
def _calculate_distance(self, lat1, lng1, lat2, lng2) -> float:
    """使用 Haversine 公式计算两点间的距离（公里）"""
    R = 6371  # 地球半径（公里）
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c
```

### 4. Phase3 验证流程

在 `_validate_and_filter_daily_plan()` 方法中，对每天的行程数据进行三重验证：

```python
def _validate_and_filter_daily_plan(self, daily_plan, destination):
    # 1. 验证景点是否在目标城市范围内
    valid_attractions = []
    for attraction in daily_plan.attractions:
        if attraction.location:
            lat = float(attraction.location.latitude)
            lng = float(attraction.location.longitude)
            if self._validate_location_in_city(lat, lng, destination):
                valid_attractions.append(attraction)
            else:
                logger.warning(f"移除不在目标城市范围内的景点: {attraction.name}")
    
    # 2. 验证同一天景点间距离（不超过 50km）
    if len(valid_attractions) > 1:
        for idx in range(len(valid_attractions) - 1):
            distance = self._calculate_distance(...)
            if distance > 50:
                logger.warning(f"景点距离较远: {distance:.2f}公里")
    
    # 3. 验证餐饮和酒店位置
    # ... 类似逻辑
```

此外，`_validate_adjacent_days()` 方法验证相邻天景点间距离不超过 100km。

## 效果

- 不在目标城市范围内的景点被自动移除，不会展示给用户
- 同一天景点间距离过远时记录警告日志，便于后续优化
- 结合工具调用搜索真实景点数据，幻觉问题从源头减少
