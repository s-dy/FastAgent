from typing import Optional, List

from src.agents import Agent, MessageState
from src.core import LLMClient, Config, HumanMessage, AIMessage
from src.core.parser import json_output_parser
from src.monitor import monitor_task_status

# 默认协调者提示词模板
DEFAULT_COORDINATOR_PROMPT = """
你是一个顶级的AI任务协调专家。你的任务是分析用户的复杂问题，并将其分解为可以并行或串行执行的子任务。

请分析以下问题，并为每个子任务指定：
1. 任务描述
2. 负责的执行者（根据执行者的专长分配）
3. 任务依赖关系（如果有）

问题: {question}

可用的执行者及其专长:
{executors_info}

请严格按照以下JSON格式输出你的任务分配计划:
```json
{{
  "tasks": [
    {{
      "id": "task_1",
      "description": "任务描述",
      "executor": "执行者名称",
      "dependencies": []
    }},
    {{
      "id": "task_2", 
      "description": "任务描述",
      "executor": "执行者名称",
      "dependencies": ["task_1"]
    }}
  ]
}}"""

DEFAULT_INTEGRATION_PROMPT = """
你是一个顶级的结果整合专家。请将各个子任务的执行结果整合成一个完整、连贯的最终答案。

原始问题: {question}

各子任务的执行结果:
{results}

请提供一个整合后的完整答案:
"""

class Coordinator:
    """
    协调者
    负责 分析任务、分配任务、整合结果
    """
    def __init__(self,llm_client: LLMClient, coordinator_prompt: Optional[str] = None, integration_prompt: Optional[str] = None):
        self.llm_client = llm_client
        self.coordinator_prompt = coordinator_prompt if coordinator_prompt else DEFAULT_COORDINATOR_PROMPT
        self.integration_prompt = integration_prompt if integration_prompt else DEFAULT_INTEGRATION_PROMPT

    def analyse(self, question: str, executors_info: str, **kwargs) -> list[dict]:
        """
        分析任务并生成执行计划

        Args:
            question: 要解决的问题
            executors_info: 执行者信息
            **kwargs: LLM调用参数

        Returns:
            任务列表
        """
        prompt = self.coordinator_prompt.format(question=question, executors_info=executors_info)
        messages = [{"role": "user", "content": prompt}]
        monitor_task_status("--- 协调者正在分析任务 ---")
        response = self.llm_client.invoke(messages, **kwargs) or ""
        if isinstance(response, AIMessage):
            response_text = response.content
        else:
            response_text = "Error: 在任务分析时返回了工具调用消息"
            monitor_task_status("Error: 在任务分析时返回了工具调用消息", level='ERROR')
            return []
        monitor_task_status(f"✅ 任务分析完成:\n{response_text}")
        try:
            tasks = json_output_parser(response_text)
            if isinstance(tasks, dict) and "tasks" in tasks:
                return tasks["tasks"]
            return []
        except Exception as e:
            monitor_task_status(f"❌ 解析任务时发生错误: {e}", level='ERROR')
            return []

    def integrate(self, question: str, results: dict[str,str], **kwargs) -> str:
        """
        整合结果
        Args:
            question: 要解决的问题
            results: 各个子任务的执行结果
            **kwargs: LLM调用参数
        Returns:
            最终答案
        """
        results_text = "\n\n".join([
            f"任务 {task_id}:\n{result}"
            for task_id, result in results.items()
        ])
        prompt = self.integration_prompt.format(question=question, results=results_text)
        messages = [{"role": "user", "content": prompt}]
        monitor_task_status("--- 协调者正在整合结果 ---")
        response = self.llm_client.invoke(messages, **kwargs) or ""
        if isinstance(response, AIMessage):
            final_answer = response.content
        else:
            final_answer = "Error: 在结果整合时返回了工具调用消息"
            monitor_task_status("Error: 在结果整合时返回了工具调用消息", level='ERROR')
        monitor_task_status(f"✅ 结果整合完成:\n{final_answer}")
        return final_answer


class Executor:
    """
    执行者
    负责 执行协调者分配的任务
    """
    def __init__(self, name: str, system_prompt: str, llm_client: LLMClient):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_client = llm_client

    def execute(self, task_description: str, context: Optional[str] = None, **kwargs) -> str:
        """
        执行任务
        Args:
            task_description: 任务描述
            context: 上下文
            **kwargs: LLM调用参数
        Returns:
            任务执行结果
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        prompt = f"任务: {task_description}"
        if context:
            prompt += f"\n\n上下文信息:\n{context}"
        messages.append({"role": "user", "content": prompt})
        monitor_task_status(f"\n-> 执行者 [{self.name}] 正在执行任务: {task_description}")
        response = self.llm_client.invoke(messages, **kwargs)

        if isinstance(response, AIMessage):
            result = response.content
        else:
            result = "Error: 执行任务时返回了工具调用消息"
            monitor_task_status("Error: 执行任务时返回了工具调用消息", level='ERROR')

        monitor_task_status(f"✅ 执行者 [{self.name}] 任务完成")
        return result

class MultiAgent(Agent):
    """
    多智能体协作
    采用 协调者-执行者 模式
    """

    def __init__(
            self,
            name: str,
            llm: LLMClient,
            state: MessageState,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
            executors: Optional[List[Executor]] = None,
    ):
        """
        初始化MultiAgent
        :param name: Agent名称
        :param llm: LLM
        :param state: 状态管理
        :param system_prompt: 系统提示词
        :param config: 配置
        :param executors: 执行者
        """
        super().__init__(name, llm, system_prompt, config)
        self.state = state
        self.coordinator = Coordinator(llm)
        self.executors: dict[str, Executor] = {}

        if executors:
            for executor in executors:
                self.register_executor(executor)

    def register_executor(self, executor: Executor):
        """
        注册执行者
        :param executor: 执行者
        """
        self.executors[executor.name] = executor
        monitor_task_status(f"✅ 注册执行者: {executor.name}")

    def _get_executors_info(self) -> str:
        """获取执行者信息描述"""
        if not self.executors:
            return "无执行者"
        info_list = []
        for name, executor in self.executors.items():
            info_list.append(f"- {name}: {executor.system_prompt[:100]}...")
        return "\n".join(info_list)

    def _execute_tasks(self, tasks: list[dict], **kwargs) -> dict[str,str]:
        """
        执行任务列表（处理依赖关系）

        Args:
            tasks: 任务列表
            **kwargs: LLM调用参数

        Returns:
            任务ID到结果的映射
        """
        results = {}
        executed = set()
        while len(executed) < len(tasks):
            progress_made = False # 是否有进展

            for task in tasks:
                task_id = task["id"]

                # 跳过已执行的任务
                if task_id in executed:
                    continue

                # 检查依赖是否都已完成
                dependencies = task.get("dependencies", [])
                if all(dep in executed for dep in dependencies):
                    # 构建上下文（依赖任务的结果）
                    context = None
                    if dependencies:
                        context = "\n\n".join([
                            f"依赖任务 {dep} 的结果:\n{results[dep]}"
                            for dep in dependencies
                        ])

                    # 执行任务
                    executor_name = task["executor"]
                    if executor_name not in self.executors:
                        monitor_task_status(
                            f"❌ 未找到执行者: {executor_name}",
                            level='ERROR'
                        )
                        results[task_id] = f"Error: 未找到执行者 {executor_name}"
                    else:
                        executor = self.executors[executor_name]
                        results[task_id] = executor.execute(
                            task["description"],
                            context,
                            **kwargs
                        )

                    executed.add(task_id)
                    progress_made = True

            # 如果一轮循环没有任何进展，说明存在循环依赖
            if not progress_made:
                monitor_task_status("❌ 检测到循环依赖，终止执行", level='ERROR')
                break

        return results


    def run(self,input_text: str, **kwargs) -> str:
        monitor_task_status(f"\n🤖 {self.name} 开始多智能体协作处理问题: {input_text}")

        # 1. 协调者分析任务
        executors_info = self._get_executors_info()
        tasks = self.coordinator.analyse(input_text, executors_info, **kwargs)
        if not tasks:
            final_answer = "无法生成有效的任务分配计划，任务终止。"
            monitor_task_status(f"\n--- 任务终止 ---\n{final_answer}")
        else:
            monitor_task_status(f"\n📋 任务分配计划: 共 {len(tasks)} 个子任务")

            # 2. 执行者执行任务
            results = self._execute_tasks(tasks, **kwargs)

            # 3. 协调者整合结果
            final_answer = self.coordinator.integrate(input_text, results, **kwargs)
            monitor_task_status(f"\n--- 任务完成 ---\n最终答案: {final_answer}")

        self.state.add_message(HumanMessage(input_text))
        self.state.add_message(AIMessage(final_answer))

        return final_answer
