from typing import List
from pydantic import BaseModel


class MemoryConfig(BaseModel):
    """Memory系统配置"""
    ### 基础配置 ###
    enable_working: bool = True # 是否启用工作记忆
    enable_episodic: bool = True # 是否启用情景记忆
    enable_semantic: bool = True # 是否启用语义记忆
    enable_perceptual: bool = False # 是否启用感知记忆

    ### 工作记忆配置 ###
    working_memory_capacity: int = 100 # 工作记忆容量
    working_memory_ttl: int = 60 # 工作记忆 TTL
    working_memory_tokens: int = 2000
    ### 情景记忆配置 ###

    ### 语义记忆配置 ###

    ### 感知记忆配置 ###
    perceptual_memory_modalities: List[str] = ["text", "image", "audio", "video"]

    ### postgres 配置 ###
    postgres_host: str = "localhost" # 数据库地址
    postgres_port: int = 5432 # 数据库端口
    postgres_database: str = "fast_agent" # 数据库名称
    postgres_user: str = "postgres" # 数据库用户名
    postgres_password: str = "123456" # 数据库密码

    ### milvus 配置 ###
    milvus_host: str = "localhost" # 数据库地址
    milvus_port: int = 19530 # 数据库端口
    milvus_collection_name: str = "fast_agents_vectors" # 数据库名称
    milvus_vector_size: int = 1024 # 向量长度
    milvus_metric_type: str = "IP" # 相似度类型
    milvus_index_type: str = "HNSW" # 索引类型
    milvus_ef_construction: int = 360 # 索引参数
    milvus_M: int = 32 # 索引参数
    milvus_ef_search: int = 128 # 索引参数

