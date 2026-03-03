import os
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AnyMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from app.observability.logger import default_logger as logger
from .tools_manager import ToolsManager


def _create_llm() -> ChatOpenAI:
    """创建 LLM 实例"""
    return ChatOpenAI(
        model=os.getenv("DASHSCOPE_MODEL_NAME", "deepseek-v3.2"),
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        temperature=0.7,
    )

async def _invoke_llm_with_tools(
    system_prompt: str,
    user_prompt: str,
    tools: List[BaseTool],
    max_iterations: int = 8,
) -> str:
    """
    使用 ReAct 模式调用 LLM，支持多轮工具调用。

    LLM 绑定工具后，如果 LLM 返回 tool_calls，则执行对应工具并将结果
    作为 ToolMessage 反馈给 LLM，循环直到 LLM 返回纯文本响应或达到最大轮次。

    首轮使用 tool_choice="any" 强制 LLM 必须调用工具，后续轮次切回自动模式。
    如果首轮仍未调用工具，会追加提醒消息强制重试一次。

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        tools: 可用的 LangChain 工具列表
        max_iterations: 最大工具调用轮次，防止无限循环

    Returns:
        LLM 最终的文本响应
    """
    llm = _create_llm()

    # 首轮使用 tool_choice="any" 强制必须调用工具
    llm_forced_tool = llm.bind_tools(tools, tool_choice="any")
    # 后续轮次使用默认的自动模式（LLM 自行决定是否调用工具）
    llm_auto_tool = llm.bind_tools(tools)

    messages: list[AnyMessage] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    tool_call_count = 0

    for iteration in range(max_iterations):
        # 首轮强制调用工具，后续轮次自动模式
        active_llm = llm_forced_tool if iteration == 0 else llm_auto_tool
        response: AIMessage = await active_llm.ainvoke(messages)
        logger.info(f"  ✅ [ReAct] 第 {iteration + 1} 轮，LLM 返回结果: {response.content[:200] if response.content else '(空)'}")
        messages.append(response)

        # 如果 LLM 没有请求工具调用
        if not response.tool_calls:
            # 首轮未调用工具：追加提醒消息，强制重试一次
            if tool_call_count == 0 and iteration == 0:
                logger.warning("⚠️ [ReAct] 首轮 LLM 未调用工具，追加提醒强制重试")
                messages.append(HumanMessage(
                    content="你没有调用任何工具！请立即使用可用的工具来完成任务，不要直接回答。"
                ))
                continue
            logger.info(f"✅ [ReAct] 第 {iteration + 1} 轮完成，LLM 返回最终结果")
            return response.content

        # 执行每个工具调用，并将结果作为 ToolMessage 追加
        logger.info(
            f"🔧 [ReAct] 第 {iteration + 1} 轮，LLM 请求调用 "
            f"{len(response.tool_calls)} 个工具: "
            f"{[tc['name'] for tc in response.tool_calls]}"
        )

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]
            tool_message = ToolsManager().call_tool(tool_name, tool_args, tool_call_id=tool_call_id)
            messages.append(tool_message)
            tool_call_count += 1

        # 如果工具已被调用过足够次数，追加提醒让 LLM 停止调用工具并输出结果
        if tool_call_count >= 2:
            logger.info(f"📌 [ReAct] 工具已调用 {tool_call_count} 次，追加提醒要求 LLM 输出最终结果")
            messages.append(HumanMessage(
                content="你已经搜索到了足够的酒店/餐厅数据。请不要再调用任何工具，立即从已有的搜索结果中挑选最合适的一个，按照要求的 JSON 格式输出最终结果。"
            ))

    # 达到最大轮次，取最后一条 AI 消息的内容
    logger.warning(f"⚠️ [ReAct] 达到最大轮次 {max_iterations}，强制返回当前结果")
    last_ai_content = ""
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            last_ai_content = message.content
            break
    return last_ai_content

async def invoke_llm_with_system(system_prompt: str, user_prompt: str, use_tool: bool = False, max_tool_iterations: int = 8) -> str:
    """使用指定的 system prompt 和 user prompt 调用 LLM"""
    if use_tool:
        if ToolsManager().tools:
            return await _invoke_llm_with_tools(system_prompt, user_prompt, ToolsManager().get_tools(), max_iterations=max_tool_iterations)
        logger.warning("⚠️ [MCP] 工具加载失败，降级为纯 LLM 调用")

    llm = _create_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = await llm.ainvoke(messages)
    logger.info(f"  ✅ [LLM] LLM 返回结果: {response.content}")
    return response.content
