import os
from typing import Optional, List, Dict
from openai import OpenAI

from src.monitor import monitor_task_status

class LLM:
    def __init__(
        self,
        model:Optional[str],
        api_key:Optional[str]=None,
        base_url:Optional[str]=None,
        provider:Optional[str]="auto",
        **kwargs
    ) -> None:
        self.model = model
        if provider == "auto":
            provider = self._auto_detect_provider(api_key, base_url)
        self.provider = provider
        api_key, base_url = self._resolve_credentials(api_key, base_url)

        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def _auto_detect_provider(self,api_key:Optional[str]=None,base_url:Optional[str]=None)->str:
        """
        自动检测LLM提供者
        """
        # 特定提供商
        if os.getenv("MODELSCOPE_API_KEY"): return "modelscope"
        if os.getenv("OPENAI_API_KEY"): return "openai"
        if os.getenv("ZHIPU_API_KEY"): return "zhipu"
        if os.getenv("DASHSCOPE_API_KEY"): return "dashscope"

        actual_api_key = api_key or os.getenv("LLM_API_KEY")
        actual_base_url = base_url or os.getenv("LLM_BASE_URL")

        if actual_base_url:
            base_url_lower = actual_base_url.lower()
            if "api-inference.modelscope.cn" in base_url_lower: return "modelscope"
            if "open.bigmodel.cn" in base_url_lower: return "zhipu"
            if "dashscope.aliyuncs.com" in base_url_lower: return "dashscope"
            if "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
                if ":11434" in base_url_lower: return "ollama"
                if ":8000" in base_url_lower: return "vllm"
                return "local"
        
        if actual_api_key:
            if actual_api_key.startswith("ms-"):
                return "modelscope"
        
        return "auto"

    def _resolve_credentials(self,api_key:Optional[str]=None,base_url:Optional[str]=None) -> tuple[str,str]:
        """
        根据provider解析API密钥和基础URL
        """
        if self.provider == "openai":
            resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
            return resolved_api_key, resolved_base_url
        elif self.provider == "modelscope":
            resolved_api_key = api_key or os.getenv("MODELSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("MODELSCOPE_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api-inference.modelscope.cn/v1/"
            return resolved_api_key, resolved_base_url
        elif self.provider == "dashscope":
            resolved_api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("DASHSCOPE_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            return resolved_api_key, resolved_base_url
        else:
            return api_key, base_url

    def invoke(self,messages:List[Dict[str,str]],temperature:float=0) -> str:
        """调用模型"""
        monitor_task_status('Strat Call LLM Model')
        try:
            response = self.client.chat.completions.create(model=self.model,messages=messages,temperature=temperature,stream=True)
            monitor_task_status('LLM Model Call Success')
            collected_context = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                # print(content,end="",flush=True)
                collected_context.append(content)
            # print()
            return "".join(collected_context)
        except Exception as e:
            monitor_task_status(str(e),level='ERROR')
            return ""

    def stream_invoke(self,messages:List[Dict[str,str]],temperature:float=0) -> str:
        """流式调用模型"""
        monitor_task_status('Strat Call LLM Model')
        try:
            response = self.client.chat.completions.create(model=self.model,messages=messages,temperature=temperature,stream=True)
            monitor_task_status('LLM Model Call Success')
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                # print(content,end="",flush=True)
                yield content
        except Exception as e:
            monitor_task_status(str(e),level='ERROR')


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    llm = LLM(os.getenv('DASHSCOPE_MODEL_NAME'))
    print(llm.invoke([{"role":"user","content": "你好"}]))
