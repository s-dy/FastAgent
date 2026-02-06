import os
from typing import Optional, List, Dict, Iterator, Union
from openai import OpenAI

from openai.types.chat import ChatCompletionChunk
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from fastagent.monitor import monitor_task_status
from fastagent.core.message import AIMessage,ToolMessage


class LLMClient:
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "",
        temperature: Optional[float] = 0.0,
        max_tokens: Optional[int] = 1024,
        timeout: Optional[int] = 60,
        **kwargs
    ) -> None:
        """
        初始化客户端。优先使用传入参数，如果未提供，则从环境变量加载。
        支持自动检测provider或使用统一的LLM_*环境变量配置。

        Args:
            model: 模型名称，如果未提供则从环境变量LLM_MODEL_ID读取
            api_key: API密钥，如果未提供则从环境变量读取
            base_url: 服务地址，如果未提供则从环境变量LLM_BASE_URL读取
            provider: LLM提供商，如果未提供则自动检测
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间，从环境变量LLM_TIMEOUT读取，默认60秒
        """
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))
        self.provider = provider or self._auto_detect_provider(api_key, base_url)
        
        if self.provider == "local":
            api_key = api_key or os.getenv("LLM_API_KEY")
            base_url = base_url or os.getenv("LLM_BASE_URL")
        else:
            api_key, base_url = self._resolve_credentials(api_key, base_url)

        if not all([api_key, base_url]):
            raise Exception("API密钥和服务地址必须被提供或在.env文件中定义。")

        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout)
        # 存储额外配置参数
        self.default_kwargs = kwargs

    def _auto_detect_provider(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> str:
        """
        自动检测LLM提供商

        检测逻辑：
        1. 优先检查特定提供商的环境变量
        2. 根据API密钥格式判断
        3. 根据base_url判断
        4. 默认返回通用配置
        """
        # 1. 检查特定提供商的环境变量
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        if os.getenv("DASHSCOPE_API_KEY"):
            return "qwen"
        if os.getenv("MODELSCOPE_API_KEY"):
            return "modelscope"
        if os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY"):
            return "kimi"
        if os.getenv("ZHIPU_API_KEY") or os.getenv("GLM_API_KEY"):
            return "zhipu"
        if os.getenv("OLLAMA_API_KEY") or os.getenv("OLLAMA_HOST"):
            return "ollama"
        if os.getenv("VLLM_API_KEY") or os.getenv("VLLM_HOST"):
            return "vllm"

        # 2. 根据API密钥格式判断
        actual_api_key = api_key or os.getenv("LLM_API_KEY")
        if actual_api_key:
            actual_key_lower = actual_api_key.lower()
            if actual_api_key.startswith("ms-"):
                return "modelscope"
            elif actual_key_lower == "ollama":
                return "ollama"
            elif actual_key_lower == "vllm":
                return "vllm"
            elif actual_key_lower == "local":
                return "local"
            elif actual_api_key.endswith(".") or "." in actual_api_key[-20:]:
                # 智谱AI的API密钥格式通常包含点号
                return "zhipu"

        # 3. 根据base_url判断
        actual_base_url = base_url or os.getenv("LLM_BASE_URL")
        if actual_base_url:
            base_url_lower = actual_base_url.lower()
            if "api.openai.com" in base_url_lower:
                return "openai"
            elif "api.deepseek.com" in base_url_lower:
                return "deepseek"
            elif "dashscope.aliyuncs.com" in base_url_lower:
                return "qwen"
            elif "api-inference.modelscope.cn" in base_url_lower:
                return "modelscope"
            elif "api.moonshot.cn" in base_url_lower:
                return "kimi"
            elif "open.bigmodel.cn" in base_url_lower:
                return "zhipu"
            elif "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
                # 本地部署检测 - 优先检查特定服务
                if ":11434" in base_url_lower or "ollama" in base_url_lower:
                    return "ollama"
                elif ":8000" in base_url_lower and "vllm" in base_url_lower:
                    return "vllm"
                elif ":8080" in base_url_lower or ":7860" in base_url_lower:
                    return "local"
                else:
                    # 根据API密钥进一步判断
                    if actual_api_key and actual_api_key.lower() == "ollama":
                        return "ollama"
                    elif actual_api_key and actual_api_key.lower() == "vllm":
                        return "vllm"
                    else:
                        return "local"
            elif any(port in base_url_lower for port in [":8080", ":7860", ":5000"]):
                # 常见的本地部署端口
                return "local"

        # 4. 默认返回auto，使用通用配置
        return "auto"

    def _resolve_credentials(self, api_key: Optional[str], base_url: Optional[str]) -> tuple[str, str]:
        """根据provider解析API密钥和base_url"""
        if self.provider == "openai":
            resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
            return resolved_api_key, resolved_base_url

        elif self.provider == "deepseek":
            resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api.deepseek.com"
            return resolved_api_key, resolved_base_url

        elif self.provider == "qwen":
            resolved_api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            return resolved_api_key, resolved_base_url

        elif self.provider == "modelscope":
            resolved_api_key = api_key or os.getenv("MODELSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api-inference.modelscope.cn/v1/"
            return resolved_api_key, resolved_base_url

        elif self.provider == "kimi":
            resolved_api_key = api_key or os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api.moonshot.cn/v1"
            return resolved_api_key, resolved_base_url

        elif self.provider == "zhipu":
            resolved_api_key = api_key or os.getenv("ZHIPU_API_KEY") or os.getenv("GLM_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://open.bigmodel.cn/api/paas/v4"
            return resolved_api_key, resolved_base_url

        elif self.provider == "ollama":
            resolved_api_key = api_key or os.getenv("OLLAMA_API_KEY") or os.getenv("LLM_API_KEY") or "ollama"
            resolved_base_url = base_url or os.getenv("OLLAMA_HOST") or os.getenv("LLM_BASE_URL") or "http://localhost:11434/v1"
            return resolved_api_key, resolved_base_url

        elif self.provider == "vllm":
            resolved_api_key = api_key or os.getenv("VLLM_API_KEY") or os.getenv("LLM_API_KEY") or "vllm"
            resolved_base_url = base_url or os.getenv("VLLM_HOST") or os.getenv("LLM_BASE_URL") or "http://localhost:8000/v1"
            return resolved_api_key, resolved_base_url

        elif self.provider == "local":
            resolved_api_key = api_key or os.getenv("LLM_API_KEY") or "local"
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "http://localhost:8000/v1"
            return resolved_api_key, resolved_base_url

        elif self.provider == "custom":
            resolved_api_key = api_key or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL")
            return resolved_api_key, resolved_base_url

        else:
            # auto或其他情况：使用通用配置，支持任何OpenAI兼容的服务
            resolved_api_key = api_key or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL")
            return resolved_api_key, resolved_base_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def invoke(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, 
               tool_choice: Optional[Union[str, Dict]] = None, **kwargs) -> Union[AIMessage, List[ToolMessage]]:
        """
        调用模型生成响应，支持工具调用
        
        Args:
            messages: 消息列表
            tools: 工具定义列表（OpenAI格式）
            tool_choice: 工具选择策略 ("auto", "none", "required" 或具体工具)
            **kwargs: 额外参数，会覆盖默认配置
            
        Returns:
            模型响应对象（包含可能的工具调用）
        """
        monitor_task_status('开始调用LLM模型',messages)
        
        # 合并默认参数和传入参数
        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": False,
        }
        
        # 添加工具相关参数
        if tools is not None:
            call_kwargs["tools"] = tools
        if tool_choice is not None:
            call_kwargs["tool_choice"] = tool_choice
            
        # 添加其他参数，排除已处理的参数
        excluded_keys = {'temperature', 'max_tokens', 'stream', 'tools', 'tool_choice'}
        for key, value in kwargs.items():
            if key not in excluded_keys:
                call_kwargs[key] = value
        for key, value in self.default_kwargs.items():
            if key not in call_kwargs and key not in excluded_keys:
                call_kwargs[key] = value

        try:
            response = self.client.chat.completions.create(**call_kwargs)
            monitor_task_status('LLM调用成功')
            msg = response.choices[0].message
            usage = response.usage
            if not msg.tool_calls:
                return AIMessage(content=msg.content,metadata={'reasoning_content': msg.reasoning_content if hasattr(msg, 'reasoning_content') else None})
            else:
                tool_calls = msg.tool_calls
                tool_msgs = []
                for tool_call in tool_calls:
                    tool_msgs.append(ToolMessage(
                        content=msg.content,
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.function.name,
                        tool_arguments=tool_call.function.arguments,
                        tool_type=tool_call.type
                    ))
                return tool_msgs

        except Exception as e:
            monitor_task_status(f"LLM调用失败: {str(e)}", level='ERROR')
            raise e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def stream_invoke(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None,
                      tool_choice: Optional[Union[str, Dict]] = None, **kwargs) -> Iterator[ChatCompletionChunk]:
        """
        流式调用模型生成响应，支持工具调用
        
        Args:
            messages: 消息列表
            tools: 工具定义列表（OpenAI格式）
            tool_choice: 工具选择策略
            **kwargs: 额外参数
            
        Yields:
            流式响应块（可能是内容块或工具调用块）
        """
        # 合并默认参数和传入参数
        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": True,
        }
        
        # 添加工具相关参数
        if tools is not None:
            call_kwargs["tools"] = tools
        if tool_choice is not None:
            call_kwargs["tool_choice"] = tool_choice
            
        # 添加其他参数，排除已处理的参数
        excluded_keys = {'temperature', 'max_tokens', 'stream', 'tools', 'tool_choice'}
        for key, value in kwargs.items():
            if key not in excluded_keys:
                call_kwargs[key] = value
        for key, value in self.default_kwargs.items():
            if key not in call_kwargs and key not in excluded_keys:
                call_kwargs[key] = value

        try:
            response = self.client.chat.completions.create(**call_kwargs)
            monitor_task_status('LLM流式调用成功')
            
            for chunk in response:
                yield chunk
                
        except Exception as e:
            monitor_task_status(f"LLM流式调用失败: {str(e)}", level='ERROR')
            raise e
