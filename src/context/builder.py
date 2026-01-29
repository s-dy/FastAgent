"""获取(Gather)- 选择(Select)- 结构化(Structure)- 压缩(Compress)"""
from utils.calculate import calculate_keyword_relevance, calculate_time_recency

"""构建并结构化上下文
[Role & Policies]：明确了 AI 的角色和回答要求
[Task]：清晰地表达了用户的问题
[Evidence]：从 RAG 系统检索的相关知识
[Context]：对话历史和相关记忆，提供了充分的背景信息
[Output]：指导 LLM 如何组织回答
"""

"""待优化
动态调整 token 预算：根据任务复杂度动态调整 max_tokens，简单任务使用较小预算，复杂任务增加预算。

相关性计算优化：在生产环境中，将简单的关键词重叠替换为向量相似度计算，提升检索质量。

缓存机制：对于不变的系统指令和知识库内容，可以实现缓存机制，避免重复计算。
"""

from datetime import datetime
import math
from typing import List, Optional

from src.context.config import ContextConfig
from src.context.base import ContextPacket
from src.core.message import Message
from src.memory.tool import MemoryTool
from src.monitor import monitor_task_status



class ContextBuilder:
    def __init__(self, config:ContextConfig, memory_tool:MemoryTool,rag_tool=None):
        self.config = config
        self.memory_tool = memory_tool
        self.rag_tool = rag_tool

    def _gather(
        self,
        user_query: str,
        conversation_history: Optional[List[Message]]=None,
        system_instruction: Optional[str]=None,
        custom_packets: Optional[List[ContextPacket]]=None
    ) -> List[ContextPacket]:
        """汇集所有候选信息

            Args:
                user_query: 用户查询
                conversation_history: 对话历史
                system_instruction: 系统指令
                custom_packets: 自定义信息包

            Returns:
                List[ContextPacket]: 候选信息列表
        """
        packets = []
        # 1. 添加系统指令(最高优先级,不参与评分)
        if system_instruction:
            packets.append(ContextPacket(
                content=system_instruction, 
                timestamp=datetime.now(),
                token_count=self._count_tokens(system_instruction),
                relevance_score=1.0, # 系统指令始终保留
                metadata={"type": "system_instruction", "priority": "high"}
            ))
        # 2. 从记忆系统检索相关记忆
        if self.memory_tool:
            try:
                memory_result = self.memory_tool.run({
                    "action" : "search",
                    "query": user_query,
                    "limit": 10,
                    "min_importance": 0.3
                })
                memory_packets = self._parse_memory_result(memory_result,user_query)
                packets.extend(memory_packets)
            except Exception as e:
                monitor_task_status(f"Error occurred while retrieving memory: {e}", level="ERROR")
        # 3. 从 RAG 系统检索相关知识
        if self.rag_tool:
            try:
                rag_result = self.rag_tool.run({
                    "action" : "search",
                    "query": user_query,
                    "limit": 10,
                    "min_relevance": 0.3
                })
                rag_packets = self._parse_rag_result(rag_result,user_query)
                packets.extend(rag_packets)
            except Exception as e:
                monitor_task_status(f"Error occurred while retrieving knowledge: {e}", level="ERROR")
        # 4. 添加对话历史(仅保留最近的 N 条)
        if conversation_history:
            recent_history = conversation_history[-5:]
            for msg in recent_history:
                packets.append(ContextPacket(
                    content=f"[{msg.role}]: {msg.content}", 
                    timestamp=msg.timestamp if hasattr(msg, "timestamp") else datetime.now(),
                    token_count=self._count_tokens(msg.content),
                    relevance_score=0.6,  # 历史消息的基础相关性
                    metadata={"type": "conversation_history", "role": msg.role}
                ))

        # 5. 添加自定义信息包
        if custom_packets:
            packets.extend(custom_packets)
        
        monitor_task_status(f"[ContextBuilder] 汇集了 {len(packets)} 个候选信息包")
        return packets
    
    def _select(
        self,
        packets: List[ContextPacket],
        user_query: str,
        available_tokens: int
    ) -> List[ContextPacket]:
        """选择最相关的信息包

        Args:
            packets: 候选信息包列表
            user_query: 用户查询(用于计算相关性)
            available_tokens: 可用的 token 数量

        Returns:
            List[ContextPacket]: 选中的信息包列表
        """
        # 1. 分离系统指令和其他信息
        system_packets = [packet for packet in packets if packet.metadata.get("type") == "system_instruction"]
        other_packets = [packet for packet in packets if packet.metadata.get("type") != "system_instruction"]
        # 2. 计算系统指令占用的 token
        system_tokens = self._count_tokens("\n\n".join([packet.content for packet in system_packets]))
        remaining_tokens = available_tokens - system_tokens
        if remaining_tokens <= 0:
            monitor_task_status("[WARNING] 系统指令已占满所有 token 预算", level="WARNING")
            return system_packets
        # 3. 为其他信息计算综合分数
        scored_packets = []
        for packet in other_packets:
            if packet.relevance_score == 0.5:
                relevance = calculate_keyword_relevance(packet.content, user_query)
                packet.relevance_score = relevance
            # 计算新近性分数
            recency = calculate_time_recency(packet.timestamp, standard=24)
            # 综合分数 = 相关性权重 × 相关性 + 新近性权重 × 新近性
            score = self.config.relevance_weight * packet.relevance_score + self.config.recency_weight * recency
            # 过滤低于最小相关性阈值的信息
            if packet.relevance_score >= self.config.min_relevance:
                scored_packets.append((score, packet))
        # 4. 按分数降序排序
        scored_packets.sort(key=lambda x: x[0], reverse=True)
        # 5. 贪心选择:按分数从高到低填充,直到达到 token 上限
        selected = system_packets.copy()
        current_tokens = system_tokens
        for score, packet in scored_packets:
            if current_tokens + packet.token_count <= available_tokens:
                selected.append(packet)
                current_tokens += packet.token_count
            else:
                break
        monitor_task_status(f"[ContextBuilder] 选择了 {len(selected)} 个信息包, 总 token 数: {current_tokens}")
        return selected

    def _structure(
        self,
        selected_packets: List[ContextPacket],
        user_query: str
    ) -> str:
        """将选中的信息包组织成结构化的上下文模板

        Args:
            selected_packets: 选中的信息包列表
            user_query: 用户查询

        Returns:
            str: 结构化的上下文字符串
        """
        system_instructions = [] # 系统指令列表
        evidence = [] # 证据列表
        context = [] # 上下文列表

        for packet in selected_packets:
            packet_type = packet.metadata.get("type")
            if packet_type == "system_instruction":
                system_instructions.append(packet.content)
            elif packet_type in ["rag_result","knowledge"]:
                evidence.append(packet.content)
            else:
                context.append(packet.content)

        sections = []
        # [Role & Policies] 系统指令
        if system_instructions: 
            sections.append("[Role & Policies]\n" + "\n".join(system_instructions))

        # [Task] 用户查询
        sections.append(f"[Task]\n{user_query}")

        # [Evidence] 证据
        if evidence:
            sections.append("[Evidence]\n" + "\n---\n".join(evidence))

        # [Context] 上下文
        if context:
            sections.append("[Context]\n" + "\n".join(context))

        # [Output] 输出
        sections.append("[Output]\n请基于以上信息,提供准确、有据的回答。")

        return "\n\n".join(sections)

    def _compress(self,context:str,max_tokens: int) -> str:
        """压缩超限的上下文

        Args:
            context: 原始上下文
            max_tokens: 最大 token 限制

        Returns:
            str: 压缩后的上下文
        """
        current_tokens = self._count_tokens(context)
        if current_tokens <= max_tokens:
            return context
        monitor_task_status(f"[ContextBuilder] 上下文长度: {current_tokens} > {max_tokens}, 需要压缩")

        # 分区压缩:保持结构完整性
        sections = context.split("\n\n")
        compressed_sections = []
        current_total = 0

        for section in sections:
            section_tokens = self._count_tokens(section)
            if current_total + section_tokens <= max_tokens:
                # 完整保留
                compressed_sections.append(section)
                current_total += section_tokens
            else:
                # 部分保留
                remaining_tokens = max_tokens - current_total
                if remaining_tokens > 50:
                    # 摘要或截断
                    truncated = self._truncate_text(section, remaining_tokens)
                    compressed_sections.append(truncated + "\n[... 内容已压缩 ...]")
                break
        
        compressed_context = "\n\n".join(compressed_sections)
        final_tokens = self._count_tokens(compressed_context)
        monitor_task_status(f"[ContextBuilder] 压缩完成: {current_tokens} -> {final_tokens} tokens")
        return compressed_context
        
    def _truncate_text(self,text: str, max_tokens: int) -> str:
        """截断文本以适应最大 token 限制

        Args:
            text: 原始文本
            max_tokens: 最大 token 限制

        Returns:
            str: 截断后的文本
        """
        # 生产环境中应该使用精确的 tokenizer
        char_per_token = len(text) / self._count_tokens(text) if self._count_tokens(text) > 0 else 4
        max_chars = int(max_tokens * char_per_token)

        return text[:max_chars]

    def _count_tokens(self, text: str) -> int:
        """计算文本的 token 数量

        Args:
            text: 输入文本

        Returns:
            int: token 数量
        """
        # 生产环境中应该使用实际的 tokenizer
        chinese_chars = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
        english_words = len([w for w in text.split() if w])

        return int(chinese_chars + english_words * 1.3)

    def build(
        self,
        user_query: str,
        conversation_history: List[Message],
        system_instruction: str,
        custom_packets: List[ContextPacket] = None
    ) -> str:
        """构建并结构化上下文

        Args:
            user_query: 用户查询
            conversation_history: 对话历史
            system_instruction: 系统指令
            custom_packets: 自定义信息包列表

        Returns:
            str: 结构化后的上下文
        """
        monitor_task_status("[ContextBuilder] 开始构建上下文")
        packets = self._gather(user_query, conversation_history, system_instruction, custom_packets)
        selected_packets = self._select(packets, user_query, available_tokens=self.config.max_tokens * 3 // 4)
        structured_context = self._structure(selected_packets, user_query)
        compressed_context = self._compress(structured_context, self.config.max_tokens)
        return compressed_context
