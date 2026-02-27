from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.common import Hotel, Attraction, Meal, WeatherInfo, Budget



class TripPlanRequest(BaseModel):
    """行程规划的API请求体"""
    destination: str = Field(..., description="目的地城市", examples=["北京"])
    start_date: str = Field(..., description="开始日期", examples=["2024-10-01"])
    end_date: str = Field(..., description="结束日期", examples=["2024-10-03"])
    preferences: List[str] = Field(default_factory=list, description="旅行偏好", examples=["历史", "美食"])
    hotel_preferences: List[str] = Field(default_factory=list, description="酒店偏好", examples=["经济型"])
    budget: str = Field(default="中等", description="预算水平（如：经济、适中、豪华）", examples=["中等"])


class DailyPlan(BaseModel):
    """单日行程"""
    day: int = Field(..., description="第几天")
    theme: str = Field("", description="当日主题")
    weather: Optional[WeatherInfo] = Field(default=None, description="当日天气信息")
    hotels: List[Hotel] = Field(default=list, description="当日推荐列表")
    attractions: List[Attraction] = Field(default_factory=list, description="当日景点列表")
    dining: List[Meal] = Field(default_factory=list, description="当日餐饮列表")
    budget: Budget = Field(default_factory=Budget, description="当日预算")


class TripPlan(BaseModel):
    """旅行计划"""
    city: str = Field(...,description="目的地城市")
    start_date: str = Field(...,description="开始日期")
    end_date: str = Field(...,description="结束日期")
    days: List[DailyPlan] = Field(default_factory=list,description="每日行程")
    weather_info: List[WeatherInfo] = Field(default_factory=list,description="天气信息")
    overall_suggestions: str = Field(...,description="总体建议")
    budget: Optional[Budget] = Field(default=None,description="预算信息")


class TripPlanResponse(BaseModel):
    """行程规划的API响应体"""
    id: Optional[str] = Field(None, description="行程ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    trip_title: str = Field(..., description="行程标题")
    total_budget: Budget = Field(..., description="整体预算（包含交通、餐饮、酒店、景点门票费用拆分）")
    days: List[DailyPlan] = Field(..., description="每日计划详情")