import os
from dotenv import load_dotenv

from src.core.llm import LLMClient

load_dotenv()

llm = LLMClient(os.getenv('DASHSCOPE_MODEL_NAME'))

# print(llm.invoke([{"role":"user","content": "你好"}]))

for content in llm.stream_invoke([{"role":"user","content": "写一个快速排序算法"}]):
    print(content,end="",flush=True)
