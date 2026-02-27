from typing import Optional, Any, Union
# from app.services.vector_memory_service import VectorMemoryService
from app.services.context_manager import ContextManager

from fastagent.core import LLMClient, AIMessage, HumanMessage, Config
from fastagent.tools import ToolRegistry
from fastagent.agents import ReactAgent, MessageState
from fastagent.monitor import monitor_task_status
from fastagent.memory import MemoryConfig, MemoryManager


class EnhancedAgent(ReactAgent):
    """
    增强的智能体基类
    在SimpleAgent基础上增加：
    - 记忆能力（检索和存储记忆）
    - 上下文感知（使用上下文管理器）
    - 通信能力（与其他智能体通信）
    """
    
    def __init__(
        self,
        name: str,
        llm: LLMClient,
        state: MessageState,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional['ToolRegistry'] = None,
        enable_tool_calling: bool = True,
        context_manager: Optional[ContextManager] = None,
        user_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        """
        初始化增强智能体
        
        Args:
            name: 智能体名称
            llm: LLM服务
            system_prompt: 系统提示词
            config: 配置
            tool_registry: 工具注册表
            enable_tool_calling: 是否启用工具调用
            context_manager: 上下文管理器
            user_id: 用户ID（用于记忆检索）
            memory_manager: 记忆管理实例
        """
        super().__init__(name, llm, state, system_prompt, config, tool_registry=tool_registry, enable_tool_calling=enable_tool_calling)
        self.context_manager = context_manager
        self.user_id = user_id
        self.memory_service = memory_manager
        
    def _get_enhanced_system_prompt(self) -> str:
        """构建增强的系统提示词，包含记忆上下文"""
        base_prompt = super()._get_system_prompt()
        # 添加记忆上下文（性能优化：只在context_manager中没有记忆时才检索）
        if self.user_id:
            # 优先从context_manager获取已检索的记忆
            memory_context = ""
            if self.context_manager:
                memories = self.context_manager.get_shared_data("memories")
                if memories:
                    # 使用已检索的记忆（避免重复检索）
                    parts = []
                    if memories:
                        mem_texts = [mem.get("text_representation", "")[:100] for mem in memories]
                        parts.append(f"用户历史记忆: {'; '.join(mem_texts)}")

                    memory_context = "\n".join(parts)
                    monitor_task_status(f"{self.name} 使用context_manager中的记忆，跳过重复检索")
            
            # 如果context_manager中没有，才进行检索（降级方案）
            if not memory_context:
                memory_context = self._get_memory_context()
                monitor_task_status(f"{self.name} context_manager中没有记忆，执行向量检索")
            
            if memory_context:
                memory_section = "\n\n## 相关记忆信息\n"
                memory_section += "以下是与当前任务相关的历史信息，你可以参考这些信息来更好地完成任务：\n"
                memory_section += memory_context + "\n"
                base_prompt += memory_section
        
        # 添加上下文信息
        if self.context_manager:
            shared_data = self.context_manager.get_all_shared_data()
            if shared_data:
                context_section = "\n\n## 共享上下文信息\n"
                context_section += "以下是从其他智能体共享的信息：\n"
                for key, value in shared_data.items():
                    context_section += f"- {key}: {str(value)[:200]}\n"
                base_prompt += context_section
        
        return base_prompt
    
    def _get_memory_context(self) -> str:
        """获取记忆上下文（使用向量记忆服务）"""
        if not self.user_id:
            return ""
        
        context_parts = []
        
        # 构建查询文本
        query_text = ""
        if self.context_manager:
            request_context = self.context_manager.get_shared_data("request")
            if request_context:
                destination = request_context.get("destination", "")
                prefs = request_context.get("preferences", [])
                query_text = f"{destination} {' '.join(prefs)}"
        
        # # 检索用户记忆
        # user_memories = self.memory_service.retrieve_user_memories(
        #     user_id=self.user_id,
        #     query=query_text,
        #     limit=3,
        #     memory_types=["preference", "trip"]
        # )
        # if user_memories:
        #     memory_texts = [mem.get("text_representation", "")[:100] for mem in user_memories]
        #     context_parts.append(f"用户历史记忆: {'; '.join(memory_texts)}")
        #
        # # 检索相关知识记忆
        # if query_text:
        #     knowledge_memories = self.memory_service.retrieve_knowledge_memories(
        #         query=query_text,
        #         limit=2,
        #         knowledge_types=["destination", "experience"]
        #     )
        #     if knowledge_memories:
        #         knowledge_texts = [mem.get("text_representation", "")[:100] for mem in knowledge_memories]
        #         context_parts.append(f"相关知识: {'; '.join(knowledge_texts)}")

        return "\n".join(context_parts)

    def run(
        self,
        input_text: str,
        *,
        tool_choice: Optional[Union[str, dict]] = None,
        **kwargs,
    ) -> str:
        """
        重写的运行方法 - 增强版，支持记忆和上下文
        """
        monitor_task_status(f"🤖 {self.name} 正在处理: {input_text[:100]}...")

        # 更新上下文
        if self.context_manager:
            self.context_manager.update_context(
                self.name,
                {"input": input_text, "status": "processing"},
                "info"
            )
        
        # 构建消息列表
        messages = []
        
        # 添加增强的系统消息
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append({"role": "system", "content": enhanced_system_prompt})
        
        # 添加历史消息
        for msg in self.state.get_messages():
            messages.append({"role": msg.role, "content": msg.content})
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": input_text})

        # 构建适用于openai的tools_schemas
        tool_schemas = self._build_tool_schemas()

        current_iteration = 0
        tool_call_count = 0
        final_response = ""

        # 工具调用次数阈值：超过此次数后引导 LLM 总结结果
        summarize_threshold = max(1, self.max_step - 2)

        while current_iteration < self.max_step:
            current_iteration += 1

            # 当接近最大迭代次数时，强制禁止工具调用，要求 LLM 直接输出文本
            current_tool_choice = tool_choice
            if current_iteration >= self.max_step:
                current_tool_choice = "none"

            response = self.llm.invoke(
                messages,
                tools=tool_schemas,
                tool_choice=current_tool_choice,
                **kwargs,
            )
            if isinstance(response, list):
                content = response[0].content
                assistant_payload: dict[str, Any] = {"role": "assistant", "content": content, "tool_calls": []}
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
                    tool_call_count += 1

                # 当工具调用次数达到阈值时，追加引导消息促使 LLM 总结
                if tool_call_count >= summarize_threshold:
                    messages.append({
                        "role": "user",
                        "content": "你已经获取了足够的信息，请不要再调用工具，直接根据已有的工具返回结果进行总结并输出最终回答。",
                    })
            else:
                final_response = response.content
                break

        # 超过最大迭代次数时的兜底措施
        if current_iteration >= self.max_step and not final_response:
            final_response = "抱歉，我无法在限定步数内完成这个任务。"

        messages.append({"role": "assistant", "content": final_response})

        self.state.add_message(HumanMessage(input_text))
        self.state.add_message(AIMessage(final_response))

        # 更新上下文
        if self.context_manager:
            self.context_manager.update_context(
                self.name,
                {"output": final_response, "status": "completed"},
                "result"
            )
            
        monitor_task_status(f"✅ {self.name} 响应完成")
        return final_response
