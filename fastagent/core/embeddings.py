"""
统一的Embedding接口，支持多种后端实现
包括：Transformer模型、Ollama、API等
"""

import asyncio
import os
from pathlib import Path
import aiohttp
from abc import ABC, abstractmethod
from typing import List, Union, Optional, Literal
from dataclasses import dataclass,field
import numpy as np
import requests
import torch
from transformers import AutoTokenizer, AutoModel

from fastagent.monitor import monitor_task_status


# 设置默认模型存储路径
DEFAULT_MODEL_CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"


@dataclass
class EmbeddingConfig:
    """Embedding配置类"""
    provider: Literal['transformer','ollama','openai','qwen','vllm']
    model_name: str  # 模型名称
    api_key: Optional[str] = None  # API密钥
    base_url: Optional[str] = None  # API基础URL
    dimension: Optional[int] = None  # 向量维度
    max_length: int = 8129  # 最大序列长度
    batch_size: int = 32  # 批处理大小
    device: str = "cpu"  # 设备: 'cpu' 或 'cuda'
    model_cache_dir: Path = field(default=DEFAULT_MODEL_CACHE_DIR)

    def __post_init__(self):
        """配置验证"""
        # 确保存储目录存在
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)



class BaseEmbedding(ABC):
    """Embedding基类"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """初始化模型或客户端"""
        pass
    
    @abstractmethod
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本为向量"""
        pass
    
    @abstractmethod
    async def async_encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """异步编码文本为向量"""
        pass
    
    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


class TransformerEmbedding:
    """基于Transformers的本地Embedding实现"""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.tokenizer = None
        self.model = None
        self._initialize()

    def _find_local_model(self, model_name: str) -> Optional[str]:
        """在本地缓存目录中查找模型"""
        # 标准化模型名称
        safe_model_name = model_name.replace("/", "--")
        model_path = self.config.model_cache_dir / safe_model_name

        # 检查模型目录是否存在且包含必要文件
        if model_path.exists():
            required_files = ["config.json", "tokenizer.json"]
            if all((model_path / file).exists() for file in required_files):
                return str(model_path)

        return None

    def _download_and_cache_model(self, model_name: str) -> str:
        """下载模型并缓存到本地"""
        safe_model_name = model_name.replace("/", "--")
        local_path = self.config.model_cache_dir / safe_model_name

        monitor_task_status(f"正在下载模型 {model_name} 到 {local_path}")

        try:
            # 下载tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            tokenizer.save_pretrained(local_path)

            # 下载model
            model = AutoModel.from_pretrained(model_name)
            model.save_pretrained(local_path)

            monitor_task_status(f"模型下载完成并保存到: {local_path}")
            return str(local_path)

        except Exception as e:
            monitor_task_status(f"模型下载失败: {e}")
            # 清理不完整的下载
            if local_path.exists():
                import shutil
                shutil.rmtree(local_path)
            raise

    def _initialize(self):
        """初始化Transformer模型"""
        try:
            # 首先尝试查找本地模型
            local_model_path = self._find_local_model(self.config.model_name)

            if local_model_path:
                # 使用本地模型
                print(f"使用本地缓存模型: {local_model_path}")
            else:
                # 下载并缓存模型
                local_model_path = self._download_and_cache_model(self.config.model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(local_model_path)

            self.model = AutoModel.from_pretrained(local_model_path)
            # 移动到指定设备
            if self.config.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.cuda()

            self.model.eval()
            print(f"✅ Transformer模型加载成功: {self.config.model_name}")

        except Exception as e:
            print(f"❌ Transformer模型加载失败: {e}")
            raise

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本为向量"""
        if isinstance(texts, str):
            texts = [texts]

        # Tokenize
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors='pt'
        )

        # 移动到GPU
        if self.config.device == "cuda" and torch.cuda.is_available():
            encoded = {k: v.cuda() for k, v in encoded.items()}

        # 获取embedding
        with torch.no_grad():
            outputs = self.model(**encoded)
            # 使用[CLS] token的表示
            embeddings = outputs.last_hidden_state[:, 0, :]

            # 转换为CPU并确保是float32类型以便numpy处理
            if embeddings.dtype in [torch.bfloat16, torch.float16]:
                embeddings = embeddings.float()

            embeddings = embeddings.cpu().numpy()

        result = [embedding.tolist() for embedding in embeddings]
        return result[0] if len(result) == 1 else result


class OllamaEmbedding(BaseEmbedding):
    """Ollama Embedding实现"""
    
    def _initialize(self):
        """初始化Ollama客户端"""
        self.api_base = self.config.base_url or "http://localhost:11434"
        monitor_task_status(f"✅ Ollama客户端初始化: {self.api_base}")
    
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本为向量"""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = []
        for text in texts:
            try:
                response = requests.post(
                    f"{self.api_base}/api/embeddings",
                    json={
                        "model": self.config.model_name,
                        "prompt": text
                    },
                    timeout=30
                )
                response.raise_for_status()
                embedding = response.json()["embedding"]
                embeddings.append(embedding)
            except Exception as e:
                monitor_task_status(f"❌ Ollama编码失败: {e}", level="ERROR")
                raise
        
        return embeddings[0] if len(embeddings) == 1 else embeddings
    
    async def async_encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """异步编码文本"""
        if isinstance(texts, str):
            texts = [texts]
        
        async def encode_single(text):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{self.api_base}/api/embeddings",
                        json={
                            "model": self.config.model_name,
                            "prompt": text
                        },
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        return data["embedding"]
                except Exception as e:
                    monitor_task_status(f"❌ Ollama异步编码失败: {e}", level="ERROR")
                    raise
        
        tasks = [encode_single(text) for text in texts]
        embeddings = await asyncio.gather(*tasks)
        return embeddings[0] if len(embeddings) == 1 else embeddings


class QwenEmbedding(BaseEmbedding):
    """阿里云百炼Embedding实现"""
    
    def _initialize(self):
        """初始化阿里云客户端"""
        api_key = self.config.api_key or os.getenv("ALIYUN_API_KEY")
        if not api_key:
            raise ValueError("阿里云API key is required")
        
        self.api_key = api_key
        self.api_base = self.config.base_url or "https://dashscope.aliyuncs.com/api/v1/services/embeddings"
        monitor_task_status(f"✅ 阿里云客户端初始化完成")
    
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本为向量"""
        if isinstance(texts, str):
            texts = [texts]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model_name,
            "input": {
                "texts": texts
            }
        }
        
        try:
            response = requests.post(
                self.api_base,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            embeddings = [item["embedding"] for item in data["output"]["embeddings"]]
            return embeddings[0] if len(embeddings) == 1 else embeddings
            
        except Exception as e:
            monitor_task_status(f"❌ 阿里云编码失败: {e}", level="ERROR")
            raise
    
    async def async_encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """异步编码文本"""
        if isinstance(texts, str):
            texts = [texts]
        
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model_name,
            "input": {
                "texts": texts
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.api_base,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    embeddings = [item["embedding"] for item in data["output"]["embeddings"]]
                    return embeddings[0] if len(embeddings) == 1 else embeddings
            except Exception as e:
                monitor_task_status(f"❌ 阿里云异步编码失败: {e}", level="ERROR")
                raise


class EmbeddingFactory:
    """Embedding工厂类"""

    _providers = {
        "transformer": TransformerEmbedding,
        "ollama": OllamaEmbedding,
        "qwen": QwenEmbedding
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: BaseEmbedding):
        """注册新的提供商"""
        cls._providers[name] = provider_class

    @classmethod
    def create_embedding(cls, config: EmbeddingConfig) -> BaseEmbedding:
        """创建Embedding实例"""
        if config.provider not in cls._providers:
            raise ValueError(f"不支持的提供商: {config.provider}")

        provider_class = cls._providers[config.provider]
        return provider_class(config)


# 便捷函数
def create_embedding(config:EmbeddingConfig) -> BaseEmbedding:
    """创建Embedding实例的便捷函数"""
    return EmbeddingFactory.create_embedding(config)
