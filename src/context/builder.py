"""获取(Gather)- 选择(Select)- 结构化(Structure)- 压缩(Compress)"""

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

from typing import List, Optional
from dataclasses import dataclass

from src.context import ContextConfig, ContextPacket
from src.core import Message
from src.tools.builtin import MemoryTool
from src.monitor import monitor_task_status
from utils.calculate import calculate_keyword_relevance, calculate_time_recency,count_tokens


@dataclass
class SectionInfo:
    """上下文段落信息，用于压缩时保持结构"""
    header: str
    content: str
    token_count: int
    is_essential: bool = False  # 是否为核心必要内容


class ContextBuilder:
    def __init__(self, 
        config:Optional[ContextConfig], 
        memory_tool:Optional[MemoryTool],
        rag_tool=None
    ):
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
            recent_history = conversation_history[-self.config.max_conversation_history:]
            for msg in recent_history:
                packets.append(ContextPacket(
                    content=str(msg), 
                    timestamp=msg.timestamp if hasattr(msg, "timestamp") else None,
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
    ) -> List[ContextPacket]:
        """选择最相关的信息包

        Args:
            packets: 候选信息包列表
            user_query: 用户查询(用于计算相关性)

        Returns:
            List[ContextPacket]: 选中的信息包列表
        """
        # 1. 分离系统指令和其他信息
        system_packets = [packet for packet in packets if packet.metadata.get("type") == "system_instruction"]
        other_packets = [packet for packet in packets if packet.metadata.get("type") != "system_instruction"]
        # 2. 计算系统指令占用的 token
        available_tokens = self.config.get_available_tokens()
        system_tokens = count_tokens("\n\n".join([packet.content for packet in system_packets]))
        remaining_tokens = available_tokens - system_tokens
        if remaining_tokens <= 0:
            monitor_task_status("[WARNING] 系统指令已占满所有 token 预算", level="WARNING")
            return system_packets
        # 3. 为其他信息计算综合分数
        scored_packets = []
        for packet in other_packets:
            # 如果相关性分数为 0.5,则自动计算关键词相关性
            if packet.relevance_score == 0.5:
                relevance = calculate_keyword_relevance(packet.content, user_query)
                packet.relevance_score = relevance
            # 计算新近性分数
            recency = calculate_time_recency(packet.timestamp, standard=24)
            # 综合分数 = 相关性权重 × 相关性 + 新近性权重 × 新近性
            score = self.config.text_relevance_weight * packet.relevance_score + self.config.time_recency_weight * recency
            # 过滤低于最小相关性阈值的信息
            if packet.relevance_score >= self.config.min_relevance:
                scored_packets.append((score, packet))
        # 4. 按分数降序排序
        scored_packets.sort(key=lambda x: x[0], reverse=True)
        # 5. 贪心选择:按分数从高到低填充,直到达到 token 上限
        selected = system_packets.copy()
        used_tokens = system_tokens
        # for score, packet in scored_packets:
        #     if used_tokens + packet.token_count <= available_tokens:
        #         selected.append(packet)
        #         used_tokens += packet.token_count
        #     else:
        #         break
        for score, packet in scored_packets:
            selected.append(packet)
            used_tokens += packet.token_count
        monitor_task_status(f"[ContextBuilder] 选择了 {len(selected)} 个信息包, 总 token 数: {used_tokens}")
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
        #组织不同类型的包
        packet_groups = {
            "system_instruction": [],
            "evidence": [],
            "context": []
        }

        # 分类整理信息包
        for packet in selected_packets:
            packet_type = packet.metadata.get("type", "")
            if packet_type == "system_instruction":
                packet_groups["system_instruction"].append(packet.content)
            elif packet_type in ["related_memory", "knowledge_base", "retrieval", "tool_result"]:
                packet_groups["evidence"].append(packet.content)
            else:
                packet_groups["context"].append(packet.content)

        # 构建结构化模板
        template_parts = []
        
        # [Role & Policies] 系统指令
        if packet_groups["system_instruction"]:
            template_parts.append("[Role & Policies]")
            template_parts.append("系统角色与规则：\n")
            for instruction in packet_groups["system_instruction"]:
                template_parts.append(f"- {instruction}")
            template_parts.append("")

        # [Task] 用户查询
        template_parts.append("[Task]")
        template_parts.append("用户问题：")
        template_parts.append(f"{user_query}")
        template_parts.append("")

        # [Evidence] 证据
        if packet_groups["evidence"]:
            template_parts.append("[Evidence]")
            template_parts.append("相关事实与知识：\n")
            for i, evidence_item in enumerate(packet_groups["evidence"], 1):
                template_parts.append(f"{i}. {evidence_item}")
            template_parts.append("")

        # [Context] 上下文
        if packet_groups["context"]:
            template_parts.append("[Context]")
            template_parts.append("对话历史与背景信息：\n")
            for context_item in packet_groups["context"]:
                template_parts.append(f"- {context_item}")
            template_parts.append("")

        # [Output] 输出
        template_parts.append("[Output]")
        template_parts.append("请基于以上信息，提供准确、有据、详细的回答。")
        template_parts.append("要求：逻辑清晰、内容完整、语言自然。")
        template_parts.append("")

        return "\n".join(template_parts)

    def _compress(self, context: str) -> str:
        """压缩超限的上下文，保持结构完整性

        Args:
            context: 原始上下文

        Returns:
            str: 压缩后的上下文
        """
        if not self.config.enable_compression:
            return context
            
        current_tokens = count_tokens(context)
        available_tokens = self.config.get_available_tokens()
        
        if current_tokens <= available_tokens:
            return context
            
        monitor_task_status(f"[ContextBuilder] 上下文长度: {current_tokens} > {available_tokens}, 需要压缩")

        # 解析上下文结构，保持段落完整性
        sections = self._parse_context_structure(context)
        
        # 按优先级压缩
        compressed_sections = self._compress_sections_smart(sections, available_tokens)
        
        # 重新组装上下文
        compressed_context = self._assemble_context(compressed_sections)
        final_tokens = count_tokens(compressed_context)
        
        monitor_task_status(f"[ContextBuilder] 压缩完成: {current_tokens} -> {final_tokens} tokens")
        return compressed_context

    def _parse_context_structure(self, context: str) -> List[SectionInfo]:
        """解析上下文结构，识别各个段落"""
        lines = context.split('\n')
        sections = []
        current_section = None
        current_lines = []
        
        section_headers = ['[Role & Policies]', '[Task]', '[Evidence]', '[Context]', '[Output]']
        
        for line in lines:
            line = line.strip()
            
            # 检测新的段落头
            if line in section_headers:
                # 保存上一个段落
                if current_section and current_lines:
                    section_content = '\n'.join(current_lines)
                    sections.append(SectionInfo(
                        header=current_section,
                        content=section_content,
                        token_count=count_tokens(section_content),
                        is_essential=(current_section in ['[Role & Policies]', '[Task]', '[Output]'])
                    ))
                
                # 开始新段落
                current_section = line
                current_lines = [line]  # 保留段落标题
            elif current_section:
                current_lines.append(line)
        
        # 保存最后一个段落
        if current_section and current_lines:
            section_content = '\n'.join(current_lines)
            sections.append(SectionInfo(
                header=current_section,
                content=section_content,
                token_count=count_tokens(section_content),
                is_essential=(current_section in ['[Role & Policies]', '[Task]', '[Output]'])
            ))
        
        return sections

    def _compress_sections_smart(self, sections: List[SectionInfo], available_tokens: int) -> List[SectionInfo]:
        """智能压缩段落，在保持结构的前提下减少token"""
        total_tokens = sum(section.token_count for section in sections)
        
        if total_tokens <= available_tokens:
            return sections
        
        # 计算需要压缩的token数
        compressed_sections = []
        
        # 优先保留核心段落（Role & Policies, Task, Output）
        essential_sections = [s for s in sections if s.is_essential]
        non_essential_sections = [s for s in sections if not s.is_essential]
        
        # 非核心段落可占用的token
        remaining_budget = available_tokens - sum(s.token_count for s in essential_sections)
        # 非核心段落的总token
        non_essential_tokens = sum(s.token_count for s in non_essential_sections)
        min_tokens_per_section = 50  # 每个段落至少保留50个token
        total_min_tokens = len(non_essential_sections) * min_tokens_per_section

        for section in sections:
            # 保留完整的核心段落
            if section.is_essential:
                compressed_sections.append(section)
                continue
            # 如果非核心段落可占用的token不足以存放非核心段落，则跳过
            if remaining_budget < 0:
                continue
            # 非核心段落可以全部保留
            if non_essential_tokens <= remaining_budget:
                compressed_sections.append(section)
                continue

            # 计算每个段落的基础最小保留token数（避免过度压缩）
            if total_min_tokens <= remaining_budget:
                # 预算充足，可以给每个段落分配基础token
                extra_budget = remaining_budget - total_min_tokens
                base_tokens = min_tokens_per_section
                if extra_budget > 0:
                    additional_tokens = int((section.token_count / non_essential_tokens) * extra_budget)
                    allocated_tokens = base_tokens + additional_tokens
                else:
                    allocated_tokens = base_tokens

                # 确保不超过原段落大小
                actual_tokens = min(allocated_tokens, section.token_count)
            else:
                # 预算不足，按比例分配但保证最小值
                proportional_tokens = max(
                    min_tokens_per_section,
                    int((section.token_count / non_essential_tokens) * remaining_budget)
                )
                # 确保不超过原段落大小
                actual_tokens = min(proportional_tokens, section.token_count)

            compressed_content = self._truncate_text_proportional(
                section.content,
                actual_tokens
            )

            compressed_sections.append(SectionInfo(
                header=section.header,
                content=compressed_content,
                token_count=count_tokens(compressed_content),
                is_essential=False
            ))

        return compressed_sections

    def _truncate_text_proportional(self, text: str, max_tokens: int) -> str:
        """按比例截断文本，保持更好的语义完整性"""
        if count_tokens(text) <= max_tokens:
            return text
            
        lines = text.split('\n')
        if len(lines) <= 1:
            # 单行文本，简单截断
            return self._truncate_text(text, max_tokens)
        
        # 多行文本，优先保留前面的重要内容
        preserved_lines = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = count_tokens(line)
            if current_tokens + line_tokens <= max_tokens:
                preserved_lines.append(line)
                current_tokens += line_tokens
            else:
                # 对最后一行进行部分截断
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 10:  # 至少保留一些内容
                    truncated_line = self._truncate_text(line, remaining_tokens)
                    preserved_lines.append(truncated_line + " [...内容已压缩...]\n")
                break
        
        return '\n'.join(preserved_lines) if preserved_lines else "[内容已压缩]"

    def _assemble_context(self, sections: List[SectionInfo]) -> str:
        """重新组装上下文"""
        parts = []
        for section in sections:
            parts.append(section.content)
        return '\n'.join(parts)
        
    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """截断文本以适应最大 token 限制

        Args:
            text: 原始文本
            max_tokens: 最大 token 限制

        Returns:
            str: 截断后的文本
        """
        char_per_token = len(text) / (count_tokens(text) or 1)
        max_chars = int(max_tokens * char_per_token)
        return text[:max_chars]

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
        # 1. Gather: 收集候选信息
        packets = self._gather(user_query, conversation_history, system_instruction, custom_packets)
        # 2. Select: 筛选与排序
        selected_packets = self._select(packets, user_query)
        # 3. Structure: 组织成结构化模板
        structured_context = self._structure(selected_packets, user_query)
        # 4. Compress: 压缩与规范化（如果超预算）
        compressed_context = self._compress(structured_context)
        return compressed_context

    def _parse_memory_result(self, memory_result: str, user_query: str) -> list[ContextPacket]:
        """解析记忆搜索结果，转换为ContextPacket列表
        
        Args:
            memory_result: MemoryTool搜索返回的结果字符串
            user_query: 用户查询
            
        Returns:
            list[ContextPacket]: 解析后的上下文包列表
        """
        result = []
        
        # 检查是否有相关记忆
        if f"未找到与 '{user_query}' 相关的记忆" in memory_result:
            return result
        
        # 按行分割结果
        lines = memory_result.strip().split('\n')
        
        # 解析每一行记忆
        for line in lines:
            line = line.strip()
            
            # 跳过标题行和空行
            if line.startswith('🔍 找到') or not line or line.startswith('['):
                continue
            
            # 解析记忆条目，格式如: "1. [工作记忆] 这是相关的工作记忆内容1 (重要性: 0.80)"
            if '. [' in line and ']' in line and '(' in line and ')' in line:
                try:
                    # 提取记忆类型
                    type_start = line.find('[') + 1
                    type_end = line.find(']')
                    memory_type = line[type_start:type_end].strip()
                    
                    # 提取内容和重要性
                    content_part = line[type_end + 1:].strip()
                    if '(' in content_part and ')' in content_part:
                        # 分离内容和重要性部分
                        paren_start = content_part.rfind('(')
                        paren_end = content_part.rfind(')')
                        
                        content = content_part[:paren_start].strip()
                        importance_str = content_part[paren_start+1:paren_end]
                        
                        # 提取重要性数值
                        if '重要性:' in importance_str:
                            importance_val = float(importance_str.replace('重要性:', '').strip())
                        else:
                            importance_val = 0.5  # 默认重要性
                        
                        # 创建ContextPacket
                        packet = ContextPacket(
                            content=content,
                            relevance_score=importance_val,
                            metadata={
                                "type": "related_memory",
                                "memory_type": memory_type.lower(),
                                "source": "memory_tool"
                            }
                        )
                        result.append(packet)
                        
                except (ValueError, IndexError) as e:
                    # 解析失败时跳过该行
                    monitor_task_status(f"解析记忆结果失败: {line}, 错误: {e}", level="WARNING")
                    continue
        
        return result