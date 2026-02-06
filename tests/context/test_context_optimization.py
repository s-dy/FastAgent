import unittest
from unittest.mock import Mock, patch

from fastagent.context.builder import ContextBuilder, SectionInfo
from fastagent.context.config import ContextConfig
from fastagent.context.base import ContextPacket
from fastagent.core.message import Message
from fastagent.tools.builtin import MemoryTool
from fastagent.memory.config import MemoryConfig
from utils.calculate import count_tokens


class TestContextBuilderOptimization(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        self.config = ContextConfig(
            max_tokens=8000,
            reserve_ratio=0.15,
            min_relevance=0.3,
            enable_compression=True,
            max_conversation_history=10,
            text_relevance_weight=0.7,
            time_recency_weight=0.3
        )
        
        # 创建真实的memory_tool
        user_id = "test_user_opt"
        session_id = "test_session_opt"
        memory_config = MemoryConfig(
            enable_working=True,
            enable_episodic=False,
            enable_semantic=False,
            enable_perceptual=False
        )
        self.real_memory_tool = MemoryTool(session_id, user_id=user_id, config=memory_config)
        
        self.context_builder = ContextBuilder(
            config=self.config,
            memory_tool=self.real_memory_tool,
            rag_tool=None
        )
        
    def test_improved_structure_formatting(self):
        """测试优化后的结构化格式"""
        packets = [
            ContextPacket(content="你是一个专业的AI助手", metadata={"type": "system_instruction"}),
            ContextPacket(content="相关事实1", metadata={"type": "related_memory"}),
            ContextPacket(content="相关事实2", metadata={"type": "related_memory"}),
            ContextPacket(content="用户历史消息", metadata={"type": "conversation_history"})
        ]
        
        user_query = "请解释人工智能的概念"
        result = self.context_builder._structure(packets, user_query)
        
        # 验证新的结构化格式
        self.assertIn("[Role & Policies]", result)
        self.assertIn("系统角色与规则：", result)
        self.assertIn("- 你是一个专业的AI助手", result)
        self.assertIn("[Task]", result)
        self.assertIn("用户问题：", result)
        self.assertIn("请解释人工智能的概念", result)
        self.assertIn("[Evidence]", result)
        self.assertIn("相关事实与知识：", result)
        self.assertIn("1. 相关事实1", result)
        self.assertIn("2. 相关事实2", result)
        self.assertIn("[Context]", result)
        self.assertIn("对话历史与背景信息：", result)
        self.assertIn("[Output]", result)
        self.assertIn("请基于以上信息，提供准确、有据、详细的回答。", result)
        
    def test_context_structure_parsing(self):
        """测试上下文结构解析"""
        context = """[Role & Policies]
系统角色与规则：

- 你是一个专业的AI助手

[Task]
用户请求：
请解释人工智能的概念

[Evidence]
相关事实与知识：

1. AI是模拟人类智能的技术
2. 机器学习是AI的重要分支

[Context]
对话历史与背景信息：

之前的对话内容

[Output]
请基于以上信息，提供准确、有据、详细的回答。"""

        sections = self.context_builder._parse_context_structure(context)
        
        # 验证解析结果
        self.assertEqual(len(sections), 5)  # 5个段落
        section_headers = [s.header for s in sections]
        self.assertIn('[Role & Policies]', section_headers)
        self.assertIn('[Task]', section_headers)
        self.assertIn('[Evidence]', section_headers)
        self.assertIn('[Context]', section_headers)
        self.assertIn('[Output]', section_headers)
        
        # 验证核心段落标记
        essential_sections = [s for s in sections if s.is_essential]
        self.assertEqual(len(essential_sections), 3)  # Role & Policies, Task, Output
        
    def test_smart_compression_preserve_structure(self):
        """测试智能压缩保持结构完整性"""
        # 创建一个很长的上下文
        long_evidence = "\n".join([f"{i}. 这是非常长的相关证据内容，用于测试压缩功能 {i}" for i in range(1000)])
        
        context = f"""[Role & Policies]
系统角色与规则：

- 你是一个专业的AI助手，专门解答技术问题

[Task]
用户请求：
请详细解释深度学习的核心概念和技术原理

[Evidence]
相关事实与知识：

{long_evidence}

[Context]
对话历史与背景信息：

用户之前询问过机器学习基础概念，现在想深入了解深度学习

[Output]
请基于以上信息，提供准确、有据、详细的回答。要求逻辑清晰、内容完整、语言自然。"""

        # 模拟token计数，让上下文超预算
        with patch('utils.calculate.count_tokens', side_effect=[10000, 6000]):  # 原始10000, 预算6000
            compressed = self.context_builder._compress(context)
            
        # 验证压缩后仍保持基本结构
        self.assertIn('[Role & Policies]', compressed)
        self.assertIn('[Task]', compressed)
        self.assertIn('[Output]', compressed)
        self.assertIn('[...内容已压缩...]', compressed)  # 应该有压缩提示
        
    def test_proportional_truncation(self):
        """测试比例截断功能"""
        long_text = "\n".join([f"这是第{i}行非常重要的内容，不应该被随意截断" for i in range(50)])
        max_tokens = 200  # 相对较小的预算
        
        # 模拟token计数
        with patch('utils.calculate.count_tokens', return_value=1000):  # 原始1000 tokens
            result = self.context_builder._truncate_text_proportional(long_text, max_tokens)
            
        # 验证结果保持多行结构且有压缩提示
        self.assertIn('\n', result)
        self.assertIn('[...内容已压缩...]', result)
        self.assertLess(len(result), len(long_text))
        
    def test_section_compression_prioritization(self):
        """测试段落压缩优先级"""
        sections = [
            SectionInfo('[Role & Policies]', '重要系统指令', 100, True),
            SectionInfo('[Task]', '用户问题描述', 50, True),
            SectionInfo('[Evidence]', '长证据内容1\n长证据内容2\n长证据内容3', 500, False),
            SectionInfo('[Context]', '对话历史', 200, False),
            SectionInfo('[Output]', '输出要求', 30, True)
        ]
        
        available_tokens = 400  # 限制较小的token预算
        
        compressed_sections = self.context_builder._compress_sections_smart(sections, available_tokens)
        
        # 验证核心段落被保留
        essential_headers = [s.header for s in compressed_sections if s.is_essential]
        self.assertIn('[Role & Policies]', essential_headers)
        self.assertIn('[Task]', essential_headers)
        self.assertIn('[Output]', essential_headers)
        
        # 验证总token数不超过预算
        total_tokens = sum(s.token_count for s in compressed_sections)
        self.assertLessEqual(total_tokens, available_tokens)
        
    def test_integration_with_real_memory(self):
        """测试与真实记忆系统的集成"""
        # 添加测试记忆
        self.real_memory_tool.run({
            "action": "add",
            "content": "深度学习是机器学习的一个重要分支，使用神经网络架构",
            "memory_type": "working",
            "importance": 0.9
        })
        
        self.real_memory_tool.run({
            "action": "add",
            "content": "卷积神经网络特别适用于图像处理任务",
            "memory_type": "working",
            "importance": 0.8
        })
        
        user_query = "深度学习在图像处理中的应用"
        system_instruction = "你是一个计算机视觉专家"
        
        result = self.context_builder.build(
            user_query=user_query,
            conversation_history=[],
            system_instruction=system_instruction
        )
        
        # 验证结果包含关键元素
        self.assertIn("深度学习", result)
        self.assertIn("图像处理", result)
        self.assertIn("[Role & Policies]", result)
        self.assertIn("[Task]", result)
        self.assertIn("[Evidence]", result)
        self.assertIn("[Output]", result)


if __name__ == "__main__":
    unittest.main()