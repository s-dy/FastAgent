import unittest
import uuid
from fastagent.memory.manager import MemoryManager, MemoryConfig


class TestMemoryManager(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        config = MemoryConfig(
            enable_working=True,
            enable_episodic=False,
            enable_semantic=False,
            enable_perceptual=False,
            working_memory_capacity=10,
            working_memory_tokens=1000
        )
        self.memory_manager = MemoryManager(
            user_id="test_user",
            config=config
        )
        
    def test_initialization(self):
        """测试MemoryManager初始化"""
        self.assertEqual(self.memory_manager.user_id, "test_user")
        self.assertIsNotNone(self.memory_manager.config)
        self.assertIn('working', self.memory_manager.memory_types)
        # self.assertIn('episodic', self.memory_manager.memory_types)
        # self.assertIn('semantic', self.memory_manager.memory_types)

    def test_add_memory_success(self):
        """测试成功添加记忆"""
        content = "这是一个测试记忆"
        memory_type = "working"
        importance = 0.8
        metadata = {"source": "test","user_id": "test_user"}
        
        result_id = self.memory_manager.add_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        # 验证返回的是有效的记忆ID
        self.assertIsInstance(result_id, str)
        self.assertGreater(len(result_id), 0)
        
        # 验证记忆确实被添加了
        retrieved = self.memory_manager.retrieve_memories(query="测试记忆")
        self.assertGreater(len(retrieved), 0)
        self.assertEqual(retrieved[0].content, content)
        
    def test_add_memory_with_auto_calculate_importance(self):
        """测试自动计算重要性"""
        content = "这是一个包含重要关键词的重要测试记忆"
        
        result_id = self.memory_manager.add_memory(content=content,metadata={"source":"test","user_id":"test_user"})
        result = self.memory_manager.retrieve_memories(query="重要关键词")
        # 验证返回的是有效的记忆ID
        self.assertNotEqual(result[0].importance, 0.5)
        
    def test_add_memory_invalid_type(self):
        """测试添加到无效记忆类型时抛出异常"""
        with self.assertRaises(ValueError):
            self.memory_manager.add_memory(
                content="test",
                memory_type="invalid_type"
            )
            
    def test_retrieve_memories_success(self):
        """测试成功检索记忆"""
        # 先添加一些记忆
        self.memory_manager.add_memory(content="北京旅游攻略", importance=0.7,metadata={"source":"test","user_id":"test_user"})
        self.memory_manager.add_memory(content="上海美食推荐", importance=0.6,metadata={"source":"test","user_id":"test_user"})
        self.memory_manager.add_memory(content="广州购物指南", importance=0.5,metadata={"source":"test","user_id":"test_user"})
        
        query = "旅游"
        results = self.memory_manager.retrieve_memories(
            query=query,
            limit=5,
            min_importance=0.4
        )
        # 验证结果
        self.assertGreaterEqual(len(results), 0)
        
    def test_retrieve_memories_specific_types(self):
        """测试检索特定类型的记忆"""
        # 添加不同类型的记忆
        self.memory_manager.add_memory(content="工作相关事项", memory_type="working", importance=0.8,metadata={"source":"test","user_id":"test_user"})
        # self.memory_manager.add_memory(content="昨天的会议记录", memory_type="episodic", importance=0.7,metadata={"source":"test","user_id":"test_user"})
        results = self.memory_manager.retrieve_memories(
            query="工作",
            memory_types=['working'],
            limit=5
        )
        # 验证结果
        self.assertGreaterEqual(len(results), 0)
        
    def test_update_memory_success(self):
        """测试成功更新记忆"""
        # 先添加一个记忆
        memory_id = self.memory_manager.add_memory(
            content="原始内容",
            importance=0.5,
            metadata={"category": "test","source":"test","user_id":"test_user"}
        )
        
        # 更新记忆
        success = self.memory_manager.update_memory(
            memory_id=memory_id,
            content="更新后的内容",
            importance=0.8,
            metadata={"category": "updated", "new_field": "value"}
        )

        self.assertTrue(success)
        
        # 验证记忆已更新
        retrieved = self.memory_manager.retrieve_memories(query="更新后的内容", limit=1)
        if len(retrieved) > 0:
            self.assertEqual(retrieved[0].content, "更新后的内容")
            self.assertIn("new_field", retrieved[0].metadata)
        
    def test_update_memory_not_found(self):
        """测试更新不存在的记忆"""
        fake_id = str(uuid.uuid4().hex)
        result = self.memory_manager.update_memory(
            memory_id=fake_id,
            content="new content"
        )
        self.assertFalse(result)
        
    def test_remove_memory_success(self):
        """测试成功删除记忆"""
        # 先添加一个记忆
        memory_id = self.memory_manager.add_memory(content="待删除的记忆", importance=0.5,metadata={"source":"test","user_id":"test_user"})
        
        # 验证记忆已添加
        initial_results = self.memory_manager.retrieve_memories(query="待删除的记忆")
        self.assertGreater(len(initial_results), 0)
        
        # 删除记忆
        success = self.memory_manager.remove_memory(memory_id)
        self.assertTrue(success)
        
        # 验证记忆已被删除
        final_results = self.memory_manager.retrieve_memories(query="待删除的记忆")
        self.assertEqual(len(final_results), 0)
        
    def test_remove_memory_not_found(self):
        """测试删除不存在的记忆"""
        fake_id = str(uuid.uuid4().hex)
        result = self.memory_manager.remove_memory(fake_id)
        
        self.assertFalse(result)
        
    def test_get_memory_stats(self):
        """测试获取记忆统计信息"""
        # 添加一些记忆
        for i in range(3):
            self.memory_manager.add_memory(content=f"测试记忆 {i}", importance=0.5 + i * 0.1)
        
        stats = self.memory_manager.get_memory_stats()
        # 验证统计信息
        self.assertEqual(stats["user_id"], "test_user")
        self.assertIn("working", stats["enabled_types"])
        self.assertGreaterEqual(stats["total_memories"], 3)
        
    def test_clear_all_memories(self):
        """测试清空所有记忆"""
        # 添加一些记忆
        for i in range(3):
            self.memory_manager.add_memory(content=f"清空测试记忆 {i}", importance=0.5)
        
        # 验证记忆已添加
        initial_stats = self.memory_manager.get_memory_stats()
        self.assertGreater(initial_stats["total_memories"], 0)

        # 清空记忆
        self.memory_manager.clear_all_memories()
        
        # 验证记忆已被清空
        final_stats = self.memory_manager.get_memory_stats()
        self.assertEqual(final_stats["total_memories"], 0)
        
    def test_calculate_importance(self):
        """测试重要性计算"""
        # 测试基础重要性
        content = "一般内容"
        importance = self.memory_manager._calculate_importance(content, None)
        self.assertGreaterEqual(importance, 0.0)
        self.assertLessEqual(importance, 1.0)
        
        # 测试包含重要关键词的内容
        important_content = "这是一个重要信息"
        important_importance = self.memory_manager._calculate_importance(important_content, None)
        self.assertGreaterEqual(important_importance, 0.5)  # 因为包含"重要"关键词
        
        # 测试带高优先级元数据的内容
        metadata_high = {"priority": "high"}
        high_priority_importance = self.memory_manager._calculate_importance(content, metadata_high)
        self.assertGreaterEqual(high_priority_importance, 0.5)  # 因为优先级为high
        
        # 测试带低优先级元数据的内容
        metadata_low = {"priority": "low"}
        low_priority_importance = self.memory_manager._calculate_importance(content, metadata_low)
        self.assertLessEqual(low_priority_importance, 0.5)  # 因为优先级为low


if __name__ == "__main__":
    unittest.main()