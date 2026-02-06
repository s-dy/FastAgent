import os
from dotenv import load_dotenv

from fastagent.core.llm import LLMClient

load_dotenv()

# llm = LLMClient(os.getenv('DASHSCOPE_MODEL_NAME'))
#
# # print(llm.invoke([{"role":"user","content": "你好"}]))
#
# for content in llm.stream_invoke([{"role":"user","content": "写一个快速排序算法"}]):
#     print(content,end="",flush=True)

llm = LLMClient("kimi-k2-thinking",api_key=os.getenv("DASHSCOPE_API_KEY"),base_url=os.getenv("DASHSCOPE_BASE_URL"))

tools = [{
        "type": "function",
        "function": {
            "name": "add",
            "description": "加法工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "参数a",
                        "default": 1,
                    },
                    "b": {
                        "type": "number",
                        "description": "参数b",
                        "default": 2,
                    }
                },
                "required": ["a", "b"],
            },
        }
    }]

msg = [{'role':'user',"content":"调用搜索工具,使用默认值"}]
print(llm.invoke(msg,tools=tools))

# 测试流式调用
# for chunk in llm.stream_invoke(msg,tools=tools):
#     print(chunk)