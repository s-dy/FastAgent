import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)

from src.monitor import monitor_task_status



class MilvusConnectionManager:
    """Milvus连接管理器 - 防止重复连接和初始化"""
    _instances = {}  # key: (host, port, collection_name) -> MilvusVectorStore instance
    _lock = threading.Lock()

    @classmethod
    def get_instance(
            cls,
            host: str = "localhost",
            port: int = 19530,
            collection_name: str = "fast_agents_vectors",
            vector_size: int = 384,
            metric_type: str = "IP",
            **kwargs
    ) -> 'MilvusVectorStore':
        """获取或创建Milvus实例（单例模式）"""
        # 创建唯一键
        key = (host, port, collection_name)

        if key not in cls._instances:
            with cls._lock:
                # 双重检查锁定
                if key not in cls._instances:
                    monitor_task_status(f"🔄 创建新的Milvus连接: {collection_name}")
                    cls._instances[key] = MilvusVectorStore(
                        host=host,
                        port=port,
                        collection_name=collection_name,
                        vector_size=vector_size,
                        metric_type=metric_type,
                        **kwargs
                    )
                else:
                    monitor_task_status(f"♻️ 复用现有Milvus连接: {collection_name}")
        else:
            monitor_task_status(f"♻️ 复用现有Milvus连接: {collection_name}")

        return cls._instances[key]


class MilvusVectorStore:
    """Milvus向量数据库存储实现"""

    def __init__(
            self,
            host: str = "localhost",
            port: int = 19530,
            collection_name: str = "hello_agents_vectors",
            vector_size: int = 384,
            metric_type: str = "IP",
            **kwargs
    ):
        """
        初始化Milvus向量存储

        Args:
            host: Milvus服务主机地址
            port: Milvus服务端口
            collection_name: 集合名称
            vector_size: 向量维度
            metric_type: 距离度量方式 (IP, L2, COSINE)
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.metric_type = metric_type.upper()

        # 索引参数
        self.index_type = kwargs.get("index_type", "HNSW")
        self.ef_construction = kwargs.get("ef_construction", 360)
        self.M = kwargs.get("M", 32)
        self.ef_search = kwargs.get("ef_search", 128)

        # 初始化客户端
        self.collection = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化Milvus客户端和集合"""
        try:
            # 连接到Milvus服务
            alias = f"{self.host}_{self.port}"
            connections.connect(
                alias=alias,
                host=self.host,
                port=self.port
            )
            monitor_task_status(f"✅ 成功连接到Milvus服务: {self.host}:{self.port}")

            # 创建或获取集合
            self._ensure_collection(alias)

        except Exception as e:
            monitor_task_status(f"❌ Milvus连接失败: {e}",level='ERROR')
            raise

    def _ensure_collection(self, alias: str):
        """确保集合存在，不存在则创建"""
        try:
            # 检查集合是否存在
            if utility.has_collection(self.collection_name, using=alias):
                self.collection = Collection(self.collection_name, using=alias)
                monitor_task_status(f"✅ 使用现有Milvus集合: {self.collection_name}")
            else:
                # 创建新集合
                fields = [
                    FieldSchema(
                        name="id",
                        dtype=DataType.VARCHAR,
                        is_primary=True,
                        max_length=65535
                    ),
                    FieldSchema(
                        name="vector",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=self.vector_size
                    ),
                    FieldSchema(
                        name="memory_type",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="user_id",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="memory_id",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="timestamp",
                        dtype=DataType.INT64
                    ),
                    FieldSchema(
                        name="modality",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="source",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="external",
                        dtype=DataType.BOOL
                    ),
                    FieldSchema(
                        name="namespace",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="is_rag_data",
                        dtype=DataType.BOOL
                    ),
                    FieldSchema(
                        name="rag_namespace",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="data_source",
                        dtype=DataType.VARCHAR,
                        max_length=256
                    ),
                    FieldSchema(
                        name="added_at",
                        dtype=DataType.INT64
                    )
                ]

                schema = CollectionSchema(
                    fields=fields,
                    description="Agent memory vectors"
                )

                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema,
                    using=alias
                )
                monitor_task_status(f"✅ 创建Milvus集合: {self.collection_name}")

            # 创建索引
            self._create_index()

            # 加载集合到内存
            self.collection.load()

        except Exception as e:
            monitor_task_status(f"❌ 集合初始化失败: {e}",level='ERROR')
            raise

    def _create_index(self):
        """创建向量索引"""
        try:
            # 检查索引是否已存在
            if len(self.collection.indexes) > 0:
                monitor_task_status(f"✅ 集合 {self.collection_name} 已存在索引")
                return

            # 创建索引
            index_params = {
                "index_type": self.index_type,
                "metric_type": self.metric_type,
                "params": {
                    "M": self.M,
                    "efConstruction": self.ef_construction
                }
            }

            self.collection.create_index(
                field_name="vector",
                index_params=index_params
            )
            monitor_task_status(f"✅ 为集合 {self.collection_name} 创建索引完成")

        except Exception as e:
            monitor_task_status(f"❌ 创建索引失败: {e}",level='ERROR')
            raise

    def add_vectors(
            self,
            vectors: List[List[float]],
            metadata: List[Dict[str, Any]],
    ) -> bool:
        """
        添加向量到Milvus

        Args:
            vectors: 向量列表
            metadata: 元数据列表

        Returns:
            bool: 是否成功
        """
        if not vectors:
            return False

        # 生成ID
        ids = [f"vec_{i}_{int(datetime.now().timestamp() * 1000000)}"
               for i in range(len(vectors))]

        # 准备插入数据
        entities = [[] for _ in range(len(self.collection.schema.fields))]

        # 填充数据
        for i, (vector, meta, point_id) in enumerate(zip(vectors, metadata, ids)):
            if len(vector) != self.vector_size:
                monitor_task_status(f"⚠️ 向量维度不匹配: 期望{self.vector_size}, 实际{len(vector)}")
                continue

            # 添加时间戳到元数据
            meta_with_timestamp = meta.copy()
            meta_with_timestamp["timestamp"] = int(datetime.now().timestamp())
            meta_with_timestamp["added_at"] = int(datetime.now().timestamp())

            # 确保布尔值正确
            if "external" in meta_with_timestamp:
                val = meta_with_timestamp.get("external")
                meta_with_timestamp["external"] = str(val).lower() in ("1", "true", "yes")

            # 按字段顺序填充数据
            entities[0].append(str(point_id))  # id
            entities[1].append(vector)  # vector
            entities[2].append(meta_with_timestamp.get("memory_type", ""))
            entities[3].append(meta_with_timestamp.get("user_id", ""))
            entities[4].append(meta_with_timestamp.get("memory_id", ""))
            entities[5].append(meta_with_timestamp.get("timestamp", 0))
            entities[6].append(meta_with_timestamp.get("modality", ""))
            entities[7].append(meta_with_timestamp.get("source", ""))
            entities[8].append(meta_with_timestamp.get("external", False))
            entities[9].append(meta_with_timestamp.get("namespace", ""))
            entities[10].append(meta_with_timestamp.get("is_rag_data", False))
            entities[11].append(meta_with_timestamp.get("rag_namespace", ""))
            entities[12].append(meta_with_timestamp.get("data_source", ""))
            entities[13].append(meta_with_timestamp.get("added_at", 0))

        if not entities[0]:  # 检查是否有有效数据
            return False

        # 插入数据
        insert_result = self.collection.insert(entities)
        self.collection.flush()

        monitor_task_status(f"✅ 成功添加 {len(entities[0])} 个向量到Milvus")
        return True

    def search_similar(
            self,
            query_vector: List[float],
            limit: int = 10,
            score_threshold: Optional[float] = None,
            where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量

        Args:
            query_vector: 查询向量
            limit: 返回结果数量限制
            score_threshold: 相似度阈值
            where: 过滤条件

        Returns:
            List[Dict]: 搜索结果
        """
        if len(query_vector) != self.vector_size:
            monitor_task_status(f"❌ 查询向量维度错误: 期望{self.vector_size}, 实际{len(query_vector)}",level='ERROR')
            return []

        # 构建搜索参数
        search_params = {
            "metric_type": self.metric_type,
            "params": {"ef": self.ef_search}
        }

        # 构建表达式
        expr = None
        if where:
            conditions = []
            for key, value in where.items():
                if isinstance(value, str):
                    conditions.append(f'{key} == "{value}"')
                elif isinstance(value, (int, float)):
                    conditions.append(f'{key} == {value}')
                elif isinstance(value, bool):
                    conditions.append(f'{key} == {str(value).lower()}')

            if conditions:
                expr = " and ".join(conditions)

        # 执行搜索
        search_result = self.collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=limit,
            expr=expr,
            output_fields=[
                "memory_type", "user_id", "memory_id", "timestamp",
                "modality", "source", "external", "namespace",
                "is_rag_data", "rag_namespace", "data_source", "added_at"
            ]
        )

        # 转换结果格式
        results = []
        for hits in search_result:
            for hit in hits:
                result = {
                    "id": hit.id,
                    "score": hit.score,
                    "metadata": {
                        "memory_type": hit.entity.get("memory_type"),
                        "user_id": hit.entity.get("user_id"),
                        "memory_id": hit.entity.get("memory_id"),
                        "timestamp": hit.entity.get("timestamp"),
                        "modality": hit.entity.get("modality"),
                        "source": hit.entity.get("source"),
                        "external": hit.entity.get("external"),
                        "namespace": hit.entity.get("namespace"),
                        "is_rag_data": hit.entity.get("is_rag_data"),
                        "rag_namespace": hit.entity.get("rag_namespace"),
                        "data_source": hit.entity.get("data_source"),
                        "added_at": hit.entity.get("added_at")
                    }
                }
                results.append(result)

        # 应用分数阈值过滤
        if score_threshold is not None:
            results = [r for r in results if r["score"] >= score_threshold]

        return results

    def delete_vectors(self, ids: List[str]) -> bool:
        """
        删除向量

        Args:
            ids: 要删除的向量ID列表

        Returns:
            bool: 是否成功
        """
        if not ids:
            return True

        # 构建表达式
        mid_list = [f'"{mid}"' for mid in ids]
        expr = f"id in [{','.join(mid_list)}]"

        # 删除数据
        self.collection.delete(expr)
        self.collection.flush()

        monitor_task_status(f"✅ 成功删除 {len(ids)} 个向量")
        return True

    def delete_memories(self, memory_ids: List[str]):
        """
        删除指定记忆（通过memory_id过滤删除）
        """
        if not memory_ids:
            return

        # 构建表达式
        mid_list = [f'"{mid}"' for mid in memory_ids]
        expr = f"memory_id in [{','.join(mid_list)}]"

        # 删除数据
        self.collection.delete(expr)
        self.collection.flush()

        monitor_task_status(f"✅ 成功按memory_id删除 {len(memory_ids)} 个Milvus向量")

    def clear_collection(self) -> bool:
        """
        清空集合

        Returns:
            bool: 是否成功
        """
        try:
            # 释放集合
            if self.collection:
                self.collection.release()

            # 删除集合并重新创建
            alias = f"{self.host}_{self.port}"
            utility.drop_collection(self.collection_name, using=alias)
            self._ensure_collection(alias)

            monitor_task_status(f"✅ 成功清空Milvus集合: {self.collection_name}")
            return True

        except Exception as e:
            monitor_task_status(f"❌ 清空集合失败: {e}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息

        Returns:
            Dict: 集合信息
        """
        try:
            stats = self.collection.num_entities

            info = {
                "name": self.collection_name,
                "entities_count": stats,
                "vector_size": self.vector_size,
                "metric_type": self.metric_type,
                "index_type": self.index_type
            }

            return info

        except Exception as e:
            monitor_task_status(f"❌ 获取集合信息失败: {e}")
            return {}

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息（兼容抽象接口）
        """
        info = self.get_collection_info()
        if not info:
            return {"store_type": "milvus", "name": self.collection_name}
        info["store_type"] = "milvus"
        return info

    def __del__(self):
        """析构函数，清理资源"""
        try:
            if hasattr(self, 'collection') and self.collection:
                self.collection.release()
        except:
            pass