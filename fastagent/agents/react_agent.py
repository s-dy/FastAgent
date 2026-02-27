import json
from typing import Optional, Union, Any

from fastagent.agents.base import Agent, MessageState
from fastagent.core import Config, LLMClient, AIMessage, HumanMessage
from fastagent.monitor import monitor_task_status
from fastagent.tools import ToolRegistry,Tool
from fastagent.tools.builtin import MCPTool


class ReactAgent(Agent):
    """
    思考-行动循环
    简单的对话React Agent，支持可选的工具调用
    """

    def __init__(
        self,
        name: str,
        llm: LLMClient,
        state: MessageState,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
        enable_tool_calling: bool = True,
        max_step: Optional[int] = None,
    ):
        """
        :param name: agent名称
        :param llm: llm调用类
        :param state: 状态管理
        :param system_prompt: 系统提示词模版
        :param config: agent配置
        :param tool_registry: 工具注册器
        :param enable_tool_calling: 是否启用工具调用
        :param max_step: 运行的最大循环步数
        """
        super().__init__(name, llm, system_prompt, config)
        self.state = state
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self.max_step = max_step if max_step else 3 if enable_tool_calling else 1

    def _get_system_prompt(self) -> str:
        """构建系统提示词，注入工具描述"""
        base_prompt = self.system_prompt or "你是一个可靠的AI助理，能够在需要时调用工具完成任务。"

        # 如果没有工具注册器、或不开启工具调用、或模型支持工具调用（无需通过构建prompt让llm调用工具）则返回基础prompt
        if not self.tool_registry or not self.enable_tool_calling or self.config.available_tools:
            return base_prompt

        # 模型不支持工具调用，构建prompt
        tools_description = self.tool_registry.get_tools_description()
        if not tools_description or tools_description == "暂无可用工具":
            return base_prompt

        prompt = base_prompt + "\n\n## 可用工具\n"
        prompt += "当你判断需要外部信息或执行动作时，可以直接通过函数调用使用以下工具：\n"
        prompt += tools_description + "\n"
        prompt += "\n请主动决定是否调用工具，合理利用多次调用来获得完备答案。"
        return prompt

    def _build_tool_schemas(self) -> Optional[list[dict[str, Any]]]:
        # 不支持工具调用
        if not self.tool_registry or not self.enable_tool_calling or not self.config.available_tools:
            return None
        # 支持工具调用
        schemas: list[dict[str, Any]] = []
        # Tool对象
        for tool in self.tool_registry.get_all_tools():
            schema = tool.to_openai_schema()
            schemas.append(schema)
        return schemas or None

    @staticmethod
    def _parse_function_call_arguments(arguments: Optional[str]) -> dict[str, Any]:
        """解析模型返回的JSON字符串参数"""
        if not arguments:
            return {}

        try:
            parsed = json.loads(arguments)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _execute_tool_call(self, tool_name: str, tool_arguments: str) -> str:
        """执行工具调用并返回字符串结果"""
        if not self.tool_registry:
            return "❌ 错误：未配置工具注册表"

        tool = self.tool_registry.get_tool(tool_name)
        if tool:
            try:
                arguments = self._parse_function_call_arguments(tool_arguments)
                typed_arguments = tool.convert_parameter_types(arguments)
                return tool.run(typed_arguments)
            except Exception as exc:
                return f"❌ 工具调用失败：{exc}"

        return f"❌ 错误：未找到工具 '{tool_name}'"

    def run(
        self,
        input_text: str,
        *,
        tool_choice: Optional[Union[str, dict]] = None,
        **kwargs,
    ) -> str:
        """
        执行函数调用范式的对话流程
        """
        messages: list[dict[str, Any]] = []
        # 添加增强后的系统提示词模版
        system_prompt = self._get_system_prompt()
        messages.append({"role": "system", "content": system_prompt})

        # 添加历史消息
        for msg in self.state.get_messages():
            messages.append({"role": msg.role, "content": msg.content})

        # 添加用户消息
        messages.append({"role": "user", "content": input_text})

        # 构建适用于openai的tools_schemas
        tool_schemas = self._build_tool_schemas()

        current_iteration = 0
        final_response = ""

        while current_iteration < self.max_step:
            current_iteration += 1

            response = self.llm.invoke(
                messages,
                tools=tool_schemas,
                tool_choice=tool_choice,
                **kwargs,
            )
            if isinstance(response, list):
                content = response[0].content
                assistant_payload: dict[str, Any] = {"role": "assistant", "content": content, "tool_calls": []}
                # 添加消息
                for tool_msg in response:
                    assistant_payload["tool_calls"].append(
                        {
                            "id": tool_msg.tool_call_id,
                            "type": tool_msg.tool_type,
                            "function": {
                                "name": tool_msg.tool_name,
                                "arguments": tool_msg.tool_arguments,
                            },
                        }
                    )
                messages.append(assistant_payload)
                # 执行工具
                for tool_msg in response:
                    tool_name = tool_msg.tool_name
                    tool_arguments = tool_msg.tool_arguments
                    result = self._execute_tool_call(tool_name, tool_arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_msg.tool_call_id,
                            "name": tool_name,
                            "content": result,
                        }
                    )
            else:
                final_response = response.content
                break

        # 超过最大迭代次数时的兜底措施
        if current_iteration >= self.max_step and not final_response:
            final_response = "抱歉，我无法在限定步数内完成这个任务。"

        messages.append({"role": "assistant", "content": final_response})

        self.state.add_message(HumanMessage(input_text))
        self.state.add_message(AIMessage(final_response))
        return final_response

    def add_tool(self, tool: Tool) -> None:
        """便捷方法：将工具注册到当前Agent"""
        if not self.tool_registry:
            self.tool_registry = ToolRegistry()

        self.tool_registry.register_tool(tool)

    def list_tools(self) -> list[Tool]:
        if self.tool_registry:
            return self.tool_registry.get_all_tools()
        return []
