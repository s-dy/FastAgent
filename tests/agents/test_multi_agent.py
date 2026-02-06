import os

from fastagent.agents import MessageState
from fastagent.agents.multi_agent import Executor, MultiAgent
from fastagent.core import LLMClient


llm = LLMClient(os.getenv('LAB_MODEL_NAME'),os.getenv("LAB_API_KEY"),os.getenv("LAB_BASE_URL"))
# 创建执行者
research_executor = Executor(
    name="研究员",
    system_prompt="你是一个专业的研究员，擅长收集和分析信息",
    llm_client=llm
)

writer_executor = Executor(
    name="写作专家",
    system_prompt="你是一个专业的写作专家，擅长撰写清晰、有条理的文档",
    llm_client=llm
)

# 创建多智能体
multi_agent = MultiAgent(
    name="多智能体系统",
    llm=llm,
    state=MessageState(),
    executors=[research_executor, writer_executor]
)

# 运行
result = multi_agent.run("请帮我研究人工智能的发展历史，并撰写一份报告")
print(result)