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
