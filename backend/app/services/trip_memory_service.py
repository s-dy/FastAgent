"""
行程情景记忆服务
基于 Milvus 向量数据库存储行程的自然语言摘要，支持语义检索。
"""
import os
import uuid
from datetime import datetime
from typing import List, Optional

from app.observability.logger import default_logger as logger
from app.config import settings


class TripMemoryService:
    """
    行程情景记忆服务 —— 基于 Milvus 的长期语义记忆。

    职责:
    1. 将行程规划结果转换为自然语言摘要
    2. 使用 sentence-transformers 生成向量并存入 Milvus
    3. 根据目的地 + 偏好进行语义检索，返回相关历史行程摘要
    """

    def __init__(self):
        self._embedding_model = None
        self._milvus_client = None
        self._collection_name = settings.MILVUS_COLLECTION_NAME
        self._vector_dim = settings.VECTOR_DIM
        self._initialized = False

    # ------------------------------------------------------------------
    # 延迟初始化（避免启动时阻塞）
    # ------------------------------------------------------------------
    def _ensure_initialized(self) -> bool:
        """延迟初始化 embedding 模型和 Milvus 连接，返回是否成功"""
        if self._initialized:
            return True

        try:
            self._init_embedding_model()
            self._init_milvus()
            self._initialized = True
            logger.info("✅ [TripMemory] Milvus 和 Embedding 模型初始化成功")
            return True
        except Exception as init_error:
            logger.warning(f"⚠️ [TripMemory] 初始化失败，情景记忆功能降级: {init_error}")
            return False

    def _init_embedding_model(self):
        """初始化 sentence-transformers 嵌入模型"""
        model_name = settings.EMBEDDING_MODEL
        cache_dir = os.getenv("HF_MODELS_PATH", None)
        hf_endpoint = settings.HF_ENDPOINT

        if hf_endpoint:
            os.environ["HF_ENDPOINT"] = hf_endpoint
        from sentence_transformers import SentenceTransformer

        self._embedding_model = SentenceTransformer(
            model_name,
            cache_folder=cache_dir,
        )
        logger.info(f"✅ [TripMemory] Embedding 模型加载成功: {model_name}")

    def _init_milvus(self):
        """初始化 Milvus 连接并确保 Collection 存在"""
        from pymilvus import MilvusClient, DataType

        milvus_uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
        self._milvus_client = MilvusClient(uri=milvus_uri)

        # 如果 Collection 不存在则创建
        if not self._milvus_client.has_collection(self._collection_name):
            from pymilvus import CollectionSchema, FieldSchema

            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2048),
                FieldSchema(name="destination", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="trip_date", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="importance", dtype=DataType.FLOAT),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self._vector_dim),
            ]
            schema = CollectionSchema(fields=fields, description="Travel trip episodic memory")
            self._milvus_client.create_collection(
                collection_name=self._collection_name,
                schema=schema,
            )

            # 创建向量索引
            index_params = self._milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                index_type="IVF_FLAT",
                metric_type="COSINE",
                params={"nlist": 128},
            )
            self._milvus_client.create_index(
                collection_name=self._collection_name,
                index_params=index_params,
            )
            logger.info(f"✅ [TripMemory] Milvus Collection 创建成功: {self._collection_name}")
        else:
            logger.info(f"✅ [TripMemory] Milvus Collection 已存在: {self._collection_name}")

        # 加载 Collection 到内存
        self._milvus_client.load_collection(self._collection_name)

    # ------------------------------------------------------------------
    # 向量编码
    # ------------------------------------------------------------------
    def _encode(self, text: str) -> List[float]:
        """将文本编码为向量"""
        embedding = self._embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    # ------------------------------------------------------------------
    # 摘要生成
    # ------------------------------------------------------------------
    @staticmethod
    def build_trip_summary(
        destination: str,
        start_date: str,
        duration: int,
        preferences: List[str],
        budget_level: str,
        attraction_names: List[str],
        hotel_names: List[str],
        total_cost: float,
        is_over_budget: bool,
    ) -> str:
        """
        将行程规划结果转换为自然语言摘要。

        自然语言格式的优势在于语义丰富，向量检索时匹配效果远优于 JSON 字符串。
        """
        preferences_text = "、".join(preferences) if preferences else "无特殊偏好"

        # 景点列表（最多展示 8 个，避免过长）
        unique_attractions = list(dict.fromkeys(attraction_names))
        attractions_text = "、".join(unique_attractions[:8])
        if len(unique_attractions) > 8:
            attractions_text += f"等{len(unique_attractions)}个景点"

        summary = (
            f"{start_date}，用户去{destination}旅行{duration}天，"
            f"偏好{preferences_text}，预算等级{budget_level}，"
            f"实际总花费{total_cost:.0f}元。"
            f"游览了{attractions_text}。"
        )

        # 酒店信息
        unique_hotels = list(dict.fromkeys(hotel_names))
        if unique_hotels:
            summary += f"住在{'、'.join(unique_hotels[:3])}。"

        if is_over_budget:
            summary += "本次行程实际花费超出预算。"

        return summary

    # ------------------------------------------------------------------
    # 存储
    # ------------------------------------------------------------------
    def save_trip_memory(
        self,
        user_id: str,
        memory_text: str,
        destination: str,
        trip_date: str,
        importance: float = 0.8,
    ) -> Optional[str]:
        """
        存储行程情景记忆到 Milvus。

        Args:
            user_id: 用户 ID
            memory_text: 自然语言摘要文本
            destination: 目的地城市
            trip_date: 行程开始日期
            importance: 重要性分数 (0-1)

        Returns:
            记忆 ID，失败返回 None
        """
        if not self._ensure_initialized():
            logger.warning("⚠️ [TripMemory] 未初始化，跳过记忆存储")
            return None

        try:
            memory_id = str(uuid.uuid4())[:16]
            embedding = self._encode(memory_text)

            data = {
                "id": memory_id,
                "user_id": user_id,
                "content": memory_text[:2000],
                "destination": destination[:120],
                "trip_date": trip_date,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "importance": importance,
                "embedding": embedding,
            }

            self._milvus_client.insert(
                collection_name=self._collection_name,
                data=[data],
            )

            logger.info(f"✅ [TripMemory] 情景记忆已存储: id={memory_id}, user={user_id}, dest={destination}")
            return memory_id
        except Exception as save_error:
            logger.error(f"❌ [TripMemory] 存储情景记忆失败: {save_error}")
            return None

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------
    def retrieve_memories(
        self,
        user_id: str,
        destination: str,
        preferences: List[str],
        limit: int = 3,
    ) -> List[str]:
        """
        检索与当前请求相关的历史行程记忆。

        使用目的地 + 偏好构建查询文本，通过向量相似度检索最相关的历史行程摘要，
        并通过 user_id 过滤确保只返回当前用户的记忆。

        Args:
            user_id: 用户 ID
            destination: 目的地城市
            preferences: 用户偏好标签列表
            limit: 返回数量上限

        Returns:
            相关历史行程摘要文本列表，失败返回空列表
        """
        if not self._ensure_initialized():
            return []

        try:
            query_text = f"{destination} {' '.join(preferences)}"
            query_embedding = self._encode(query_text)

            results = self._milvus_client.search(
                collection_name=self._collection_name,
                data=[query_embedding],
                limit=limit,
                filter=f'user_id == "{user_id}"',
                output_fields=["content", "destination", "trip_date", "importance"],
                search_params={"metric_type": "COSINE", "params": {"nprobe": 16}},
            )

            memory_texts = []
            for hits in results:
                for hit in hits:
                    entity = hit.get("entity", {})
                    content = entity.get("content", "")
                    if content:
                        memory_texts.append(content)

            logger.info(f"✅ [TripMemory] 检索到 {len(memory_texts)} 条相关记忆 (user={user_id}, dest={destination})")
            return memory_texts
        except Exception as search_error:
            logger.error(f"❌ [TripMemory] 检索情景记忆失败: {search_error}")
            return []

    # ------------------------------------------------------------------
    # 构建 memory_context 文本（情景记忆部分）
    # ------------------------------------------------------------------
    def build_memory_context(
        self,
        user_id: str,
        destination: str,
        preferences: List[str],
        limit: int = 3,
    ) -> str:
        """
        检索相关历史行程并格式化为可注入 Prompt 的文本。

        Returns:
            格式化的历史行程记忆文本，无记忆时返回空字符串
        """
        memory_texts = self.retrieve_memories(user_id, destination, preferences, limit)
        if not memory_texts:
            return ""

        lines = ["相关历史行程:"]
        for text in memory_texts:
            lines.append(f"  - {text[:200]}")
        return "\n".join(lines)


# 全局单例（延迟初始化，不会在 import 时阻塞）
trip_memory_service = TripMemoryService()
