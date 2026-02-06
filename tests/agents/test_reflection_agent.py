import os

from fastagent.agents import MessageState
from fastagent.agents.reflection_agent import ReflectionAgent
from fastagent.core import LLMClient

llm = LLMClient(os.getenv('DASHSCOPE_MODEL_NAME'),os.getenv("DASHSCOPE_API_KEY"),os.getenv("DASHSCOPE_BASE_URL"))
agent = ReflectionAgent("test-reflection_agent",llm=llm,state=MessageState())

question = '写一段python代码，找出1到n之间所有的素数'

print(agent.run(question))
