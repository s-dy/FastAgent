import os

from fastagent.agents import MessageState
from fastagent.agents.plan_and_execute_agent import PlanAndExecuteAgent
from fastagent.core import LLMClient


llm = LLMClient("kimi-k2-thinking",api_key=os.getenv("DASHSCOPE_API_KEY"),base_url=os.getenv("DASHSCOPE_BASE_URL"))
agent = PlanAndExecuteAgent(name="Test-PlanAndExecuteAgent", llm=llm, state=MessageState())

question = "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"
print(agent.run(question))


"""
目前的plan_and_execute Agent暂时不支持工具调用。
若需要工具调用，目前的想法是可以重构Executor模块，在Executor中复用ReactAgent。从而实现plan与工具调用结合。
"""