"""
用户偏好画像服务
基于 Redis Hash 存储用户的长期偏好画像，支持增量更新和读取。
"""
import json
from datetime import datetime
from typing import Dict, Any, List

from app.observability.logger import default_logger as logger
from app.services.redis_service import redis_service


# Redis Key 前缀
_PROFILE_KEY_PREFIX = "user_profile:"


def _profile_key(user_id: str) -> str:
    return f"{_PROFILE_KEY_PREFIX}{user_id}"


def _empty_profile() -> Dict[str, Any]:
    """返回空的用户偏好画像"""
    return {
        "trip_count": 0,
        "last_trip_date": "",
        "preferred_categories": {},
        "preferred_budget": {},
        "hotel_preferences": {},
        "visited_cities": [],
        "visited_attractions": [],
        "avg_daily_budget": 0.0,
    }


class UserProfileService:
    """用户偏好画像服务 —— 基于 Redis Hash 的长期记忆"""

    def __init__(self):
        self._redis = redis_service.redis

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """
        读取用户偏好画像。

        如果 Redis 不可用或用户无画像，返回空画像（降级策略）。
        """
        try:
            raw = self._redis.hgetall(_profile_key(user_id))
            if not raw:
                return _empty_profile()

            return {
                "trip_count": int(raw.get("trip_count", 0)),
                "last_trip_date": raw.get("last_trip_date", ""),
                "preferred_categories": json.loads(raw.get("preferred_categories", "{}")),
                "preferred_budget": json.loads(raw.get("preferred_budget", "{}")),
                "hotel_preferences": json.loads(raw.get("hotel_preferences", "{}")),
                "visited_cities": json.loads(raw.get("visited_cities", "[]")),
                "visited_attractions": json.loads(raw.get("visited_attractions", "[]")),
                "avg_daily_budget": float(raw.get("avg_daily_budget", 0)),
            }
        except Exception as read_error:
            logger.warning(f"⚠️ [UserProfile] 读取用户画像失败，降级为空画像: {read_error}")
            return _empty_profile()

    # ------------------------------------------------------------------
    # 写入 / 增量更新
    # ------------------------------------------------------------------
    def update_after_trip(
        self,
        user_id: str,
        destination: str,
        preferences: List[str],
        budget_level: str,
        hotel_preferences: List[str],
        attraction_names: List[str],
        actual_total_cost: float,
        trip_days: int,
    ) -> None:
        """
        行程规划完成后，增量更新用户偏好画像。

        Args:
            user_id: 用户 ID
            destination: 目的地城市
            preferences: 用户偏好标签列表（如 ["历史文化", "美食"]）
            budget_level: 预算等级（如 "中等"）
            hotel_preferences: 酒店偏好标签列表
            attraction_names: 本次行程涉及的所有景点名称
            actual_total_cost: 本次行程实际总花费
            trip_days: 行程天数
        """
        try:
            profile = self.get_profile(user_id)

            # 行程次数 & 日期
            profile["trip_count"] += 1
            profile["last_trip_date"] = datetime.now().strftime("%Y-%m-%d")

            # 偏好频次
            for pref in preferences:
                profile["preferred_categories"][pref] = profile["preferred_categories"].get(pref, 0) + 1
            profile["preferred_budget"][budget_level] = profile["preferred_budget"].get(budget_level, 0) + 1
            for hotel_pref in hotel_preferences:
                profile["hotel_preferences"][hotel_pref] = profile["hotel_preferences"].get(hotel_pref, 0) + 1

            # 去过的城市 & 景点（去重）
            if destination not in profile["visited_cities"]:
                profile["visited_cities"].append(destination)
            for name in attraction_names:
                if name not in profile["visited_attractions"]:
                    profile["visited_attractions"].append(name)

            # 平均每日预算（滑动平均）
            actual_daily = actual_total_cost / max(trip_days, 1)
            old_avg = profile["avg_daily_budget"]
            old_count = profile["trip_count"] - 1
            if old_count > 0:
                profile["avg_daily_budget"] = (old_avg * old_count + actual_daily) / profile["trip_count"]
            else:
                profile["avg_daily_budget"] = actual_daily

            self._save(user_id, profile)
            logger.info(f"✅ [UserProfile] 用户画像已更新: user_id={user_id}, trip_count={profile['trip_count']}")
        except Exception as update_error:
            logger.error(f"❌ [UserProfile] 更新用户画像失败: {update_error}")

    # ------------------------------------------------------------------
    # 构建 memory_context 文本
    # ------------------------------------------------------------------
    def build_memory_context(self, user_id: str, destination: str) -> str:
        """
        将用户偏好画像转换为自然语言文本，用于注入到 LLM Prompt 中。

        Args:
            user_id: 用户 ID
            destination: 当前请求的目的地

        Returns:
            自然语言描述的偏好上下文，如果无画像则返回空字符串
        """
        profile = self.get_profile(user_id)
        if profile["trip_count"] == 0:
            return ""

        parts: List[str] = []

        # 偏好排名
        top_categories = sorted(
            profile["preferred_categories"].items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        if top_categories:
            top_text = "、".join([f"{category}({count}次)" for category, count in top_categories])
            parts.append(f"用户历史偏好: {top_text}")

        # 平均预算
        if profile["avg_daily_budget"] > 0:
            parts.append(f"历史平均每日预算约{profile['avg_daily_budget']:.0f}元")

        # 是否去过当前目的地
        if destination in profile.get("visited_cities", []):
            parts.append(f"用户曾去过{destination}，请尽量推荐新的景点和餐厅")

        # 酒店偏好
        top_hotel_prefs = sorted(
            profile.get("hotel_preferences", {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )[:2]
        if top_hotel_prefs:
            hotel_text = "、".join([pref for pref, _ in top_hotel_prefs])
            parts.append(f"酒店偏好: {hotel_text}")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # 获取已去过的景点（用于程序化过滤）
    # ------------------------------------------------------------------
    def get_visited_attractions(self, user_id: str) -> List[str]:
        """返回用户去过的所有景点名称列表"""
        profile = self.get_profile(user_id)
        return profile.get("visited_attractions", [])

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _save(self, user_id: str, profile: Dict[str, Any]) -> None:
        """将画像数据序列化后写入 Redis Hash"""
        key = _profile_key(user_id)
        mapping = {
            "trip_count": str(profile["trip_count"]),
            "last_trip_date": profile["last_trip_date"],
            "preferred_categories": json.dumps(profile["preferred_categories"], ensure_ascii=False),
            "preferred_budget": json.dumps(profile["preferred_budget"], ensure_ascii=False),
            "hotel_preferences": json.dumps(profile["hotel_preferences"], ensure_ascii=False),
            "visited_cities": json.dumps(profile["visited_cities"], ensure_ascii=False),
            "visited_attractions": json.dumps(profile["visited_attractions"], ensure_ascii=False),
            "avg_daily_budget": str(profile["avg_daily_budget"]),
        }
        self._redis.hset(key, mapping=mapping)


# 全局单例
user_profile_service = UserProfileService()
