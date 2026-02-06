import unittest
from fastagent.memory import MemoryConfig
from fastagent.tools.builtin import MemoryTool


class TestMemoryTool(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        self.user_id = "test_user"
        self.session_id = "test_1111"
        self.config = MemoryConfig(
            enable_working=True,
            enable_episodic=False,
            enable_semantic=False,
            enable_perceptual=False
        )
        self.memory_tool = MemoryTool(
            self.session_id, 
            user_id=self.user_id, 
            config=self.config
        )
    
    def test_add_memory(self):
        """测试添加记忆功能"""
        # 测试添加工作记忆
        result = self.memory_tool.run({
            'action': 'add',
            "content": "这是测试工作记忆",
            "memory_type": "working",
            "importance": 0.5,
            "metadata": {"category": "test"}
        })
        self.assertIn("✅ 记忆已添加", result)
        
        # # 测试添加情景记忆
        # result = self.memory_tool.run({
        #     'action': 'add',
        #     "content": "这是测试情景记忆",
        #     "memory_type": "episodic",
        #     "importance": 0.8,
        #     "metadata": {"event": "meeting"}
        # })
        # self.assertIn("✅ 记忆已添加", result)
        
        # # 测试添加语义记忆
        # result = self.memory_tool.run({
        #     'action': 'add',
        #     "content": "这是测试语义记忆",
        #     "memory_type": "semantic",
        #     "importance": 0.6,
        #     "metadata": {"knowledge": "fact"}
        # })
        # self.assertIn("✅ 记忆已添加", result)
        
    def test_search_memory(self):
        """测试搜索记忆功能"""
        # 先添加一些记忆
        self.memory_tool.run({
            'action': 'add',
            "content": "北京是中国的首都",
            "memory_type": "working",
            "importance": 0.9,
        })
        self.memory_tool.run({
            'action': 'add',
            "content": "上海是一个国际大都市",
            "memory_type": "working",
            "importance": 0.8,
        })
        
        # 搜索记忆
        result = self.memory_tool.run({
            'action': 'search',
            "query": "中国",
            "memory_types": ["working"],
            "min_importance": 0.1,
            "limit": 5
        })
        self.assertIn("中国", result)
        self.assertIn("首都", result)
        
    def test_update_memory(self):
        """测试更新记忆功能"""
        # 先添加一个记忆
        result = self.memory_tool.run({
            'action': 'add',
            "content": "原始内容",
            "memory_type": "working",
            "importance": 0.5,
        })
        # 提取记忆ID
        if "ID:" in result:
            memory_id = result.split("ID: ")[1].split(")")[0]
            
            # 更新记忆
            update_result = self.memory_tool.run({
                'action': 'update',
                "memory_id": memory_id,
                "content": "更新后的内容",
                "importance": 0.9,
                "category": "updated"
            })
            self.assertIn("✅ 记忆已更新", update_result)
        
    def test_remove_memory(self):
        """测试删除记忆功能"""
        # 先添加一个记忆
        result = self.memory_tool.run({
            'action': 'add',
            "content": "待删除的记忆",
            "memory_type": "working",
            "importance": 0.5,
        })
        
        # 提取记忆ID
        if "ID:" in result:
            memory_id = result.split("ID: ")[1].split(")")[0]
            
            # 删除记忆
            remove_result = self.memory_tool.run({
                'action': 'remove',
                "memory_id": memory_id
            })
            
            self.assertIn("✅ 记忆已删除", remove_result)
        
    def test_stats_and_summary(self):
        """测试获取统计和摘要功能"""
        # 添加几个记忆
        for i in range(3):
            self.memory_tool.run({
                'action': 'add',
                "content": f"测试记忆 {i}",
                "memory_type": "working",
                "importance": 0.5 + i * 0.1,
            })
        
        # 获取统计信息
        stats_result = self.memory_tool.run({
            'action': 'stats'
        })
        self.assertIn("总记忆数:", stats_result)
        self.assertIn("记忆系统统计", stats_result)
        
        # 获取摘要
        summary_result = self.memory_tool.run({
            'action': 'summary',
            "limit": 5
        })
        self.assertIn("记忆系统摘要", summary_result)
        
    def test_forget_and_consolidate(self):
        """测试遗忘和整合功能"""
        # 添加一些记忆
        for i in range(5):
            importance = 0.3 if i < 3 else 0.8  # 前3个重要性低，后2个重要性高
            self.memory_tool.run({
                'action': 'add',
                "content": f"可遗忘记忆 {i}",
                "memory_type": "working",
                "importance": importance,
            })
        
        # 测试遗忘功能
        forget_result = self.memory_tool.run({
            'action': 'forget',
            "strategy": "importance_based",
            "threshold": 0.5
        })
        
        self.assertIn("已遗忘", forget_result)
        print(self.memory_tool.run({"action":"stats"}))
        
        # 测试整合功能
        consolidate_result = self.memory_tool.run({
            'action': 'consolidate',
            "from_type": "working",
            "to_type": "episodic",
            "importance_threshold": 0.7
        })
        
        self.assertIn("已整合", consolidate_result)
        
    def test_clear_all(self):
        """测试清空所有记忆功能"""
        # 添加一些记忆
        for i in range(2):
            self.memory_tool.run({
                'action': 'add',
                "content": f"清空测试记忆 {i}",
                "memory_type": "working",
                "importance": 0.5,
            })
        
        # 获取统计确认记忆已添加
        stats_before = self.memory_tool.run({
            'action': 'stats'
        })
        print(stats_before)
        
        # 清空所有记忆
        clear_result = self.memory_tool.run({
            'action': 'clear_all'
        })
        stats_after = self.memory_tool.run({
            'action': 'stats'
        })
        print(stats_after)
        
        self.assertIn("已清空所有记忆", clear_result)
        
        # 验证记忆已清空
        stats_after = self.memory_tool.run({
            'action': 'stats'
        })
        
        self.assertIn("总记忆数: 0", stats_after)
        
    def test_unsupported_action(self):
        """测试不支持的操作"""
        result = self.memory_tool.run({
            'action': 'unsupported_action'
        })
        
        self.assertIn("不支持的操作", result)
        
    def test_auto_record_conversation(self):
        """测试自动记录对话功能"""
        user_input = "用户询问天气情况"
        agent_response = "今天天气晴朗，温度适宜"
        
        # 调用自动记录对话功能
        self.memory_tool.auto_record_conversation(user_input, agent_response)
        stats_after = self.memory_tool.run({
            'action': 'stats'
        })
        print(stats_after)
        # 验证对话内容被记录
        search_result = self.memory_tool.run({
            'action': 'search',
            "query": "天气",
            "memory_types": ["working"],
        })
        print(search_result)
        self.assertIn("天气", search_result)


if __name__ == "__main__":
    # 运行单元测试
    print("Running unit tests...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
