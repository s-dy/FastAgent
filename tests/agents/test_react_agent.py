import os
from dotenv import load_dotenv

from src.agents import MessageState,ReactAgent
from src.core import LLMClient
from src.tools import ToolRegistry, Tool, ToolParameter
from src.tools.builtin import MCPTool

load_dotenv()


llm = LLMClient("kimi-k2-thinking",api_key=os.getenv("DASHSCOPE_API_KEY"),base_url=os.getenv("DASHSCOPE_BASE_URL"))
agent = ReactAgent(name="test_sample_agent",llm=llm,state=MessageState(),tool_registry=ToolRegistry())

agent.add_tool(MCPTool("http://localhost:8080/mcp"))

class AddTool(Tool):
    def __init__(self):
        super().__init__("add_tool", "add two numbers")

    def run(self, parameters: dict) -> str:
        a = parameters["a"]
        b = parameters["b"]
        return str(a + b)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="a",type="number",description="a"),
            ToolParameter(name="b",type="number",description="b")
        ]

agent.add_tool(AddTool())

agent.add_tool(MCPTool("/Users/sdy/TravelAgent/tests/protocols/mcp/server.py"))

# response = agent.run("调用加法工具，将1加2")
response = agent.run("搜索python的相关文章")
# response = agent.run("对张三生成友好的问候语")
# response = agent.run("你是如何知道你可以调用哪些工具的？工具清单是通过prompt传递给你的吗？")
print(response)

# 数据流向
# 1. MCP发现工具，并自动展开为Tool对象（name会添加prefix前缀，会存储一份真实的mcp函数名称）
# 2. ToolRegistry注册mcp发现的工具
# 3. 调用Tool对象时，会调用mcp_wrapper_tool包装后的run，自动获取真实的mcp函数名称