from typing import Optional, Dict

from src.agents import Agent, MessageState
from src.core import LLMClient, Config, AIMessage, HumanMessage
from src.monitor import monitor_task_status

# 默认提示词模板
DEFAULT_PROMPTS = {
    "initial": """
请根据以下要求完成任务：

任务: {task}

请提供一个完整、准确的回答。
""",
    "reflect": """
请仔细审查以下回答，并找出可能的问题或改进空间：

# 原始任务:
{task}

# 当前回答:
{content}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。
""",
    "refine": """
请根据反馈意见改进你的回答：

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。
"""
}

class ReflectionAgent(Agent):
    """
    Reflection Agent - 自我反思与迭代优化的智能体

    这个Agent能够：
    1. 执行初始任务
    2. 对结果进行自我反思
    3. 根据反思结果进行优化
    4. 迭代改进直到满意

    特别适合代码生成、文档写作、分析报告等需要迭代优化的任务。

    支持多种专业领域的提示词模板，用户可以自定义或使用内置模板。
    """

    def __init__(
            self,
            name: str,
            llm: LLMClient,
            state: MessageState,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
            max_iterations: int = 3,
            custom_prompts: Optional[Dict[str, str]] = None
    ):
        """
        初始化ReflectionAgent

        Args:
            name: Agent名称
            llm: LLM实例
            state: 状态管理
            system_prompt: 系统提示词
            config: 配置对象
            max_iterations: 最大迭代次数
            custom_prompts: 自定义提示词模板 {"initial": "", "reflect": "", "refine": ""}
        """
        super().__init__(name, llm, system_prompt, config)
        self.max_iterations = max_iterations
        self.state = state

        # 设置提示词模板：用户自定义优先，否则使用默认模板
        self.prompts = custom_prompts if custom_prompts else DEFAULT_PROMPTS

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行Reflection Agent

        Args:
            input_text: 任务描述
            **kwargs: 其他参数

        Returns:
            最终优化后的结果
        """
        monitor_task_status(f"\n🤖 {self.name} 开始处理任务: {input_text}")
        self.state.add_message(HumanMessage(input_text))

        # 1. 初始执行
        monitor_task_status("\n--- 正在进行初始尝试 ---")
        initial_prompt = self.prompts["initial"].format(task=input_text)
        initial_result = self._get_llm_response(initial_prompt, **kwargs)
        self.state.add_message(AIMessage(initial_result))

        # 2. 迭代循环：反思与优化
        final_answer = initial_result
        for i in range(self.max_iterations):
            monitor_task_status(f"\n--- 第 {i + 1}/{self.max_iterations} 轮迭代 ---")
            # a. 反思
            monitor_task_status("\n-> 正在进行反思...")
            last_result = self.state.get_latest_message()
            reflect_prompt = self.prompts["reflect"].format(
                task=input_text,
                content=last_result.content
            )
            feedback = self._get_llm_response(reflect_prompt, **kwargs)
            self.state.add_message(AIMessage(feedback))

            # b. 检查是否需要停止
            if "无需改进" in feedback or "no need for improvement" in feedback.lower():
                monitor_task_status("\n✅ 反思认为结果已无需改进，任务完成。")
                break

            # c. 优化
            monitor_task_status("\n-> 正在进行优化...")
            refine_prompt = self.prompts["refine"].format(
                task=input_text,
                last_attempt=last_result,
                feedback=feedback
            )
            refined_result = self._get_llm_response(refine_prompt, **kwargs)
            final_answer = refined_result
            self.state.add_message(AIMessage(refined_result))

        monitor_task_status(f"\n--- 任务完成 ---\n最终结果:\n{final_answer}")

        # # 保存到历史记录
        # self.state.add_message(HumanMessage(input_text))
        # self.state.add_message(AIMessage(final_answer))

        return final_answer

    def _get_llm_response(self, prompt: str, **kwargs) -> str:
        """调用LLM并获取完整响应"""
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages, **kwargs)
        if isinstance(response, list):
            monitor_task_status("暂不支持工具调用",level='ERROR')
            raise ValueError("暂不支持工具调用")
        else:
            return response.content

