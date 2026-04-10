from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    应用配置类
    """
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    # 日志级别
    LOG_LEVEL: str = "INFO"

    # JWT 认证配置
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_EXPIRY_HOURS: int = 24

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DECODE_RESPONSES: bool = True

    # 密码加密配置
    BCRYPT_ROUNDS: int = 12

    # 向量数据库配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_NAME: str = "travel_agent"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_DIM: int = 384

    # MCP 缓存配置
    MCP_CACHE_ENABLED: bool = True

    # HuggingFace 配置
    HF_ENDPOINT: str = "https://hf-mirror.com"
    HF_HUB_OFFLINE: bool = False
    HF_HUB_CACHE_DIR: Optional[str] = None

    def get_cors_origins_list(self) -> List[str]:
        """获取CORS origins列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]

# 创建一个全局可用的配置实例
settings = Settings()
