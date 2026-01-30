import unittest
import uuid
from datetime import datetime, timedelta
from src.memory import MemoryConfig, MemoryItem
from src.memory.store import MemoryStore
from src.memory.memory_types import WorkingMemory


class TestWorkingMemory(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        config = MemoryConfig(
            enable_working=True,
            enable_semantic=False,
            enable_perceptual=False,
            enable_episodic=False,
            working_memory_capacity=10,
            working_memory_tokens=100,
            working_memory_ttl=30  # 30分钟TTL
        )
        self.working_memory = WorkingMemory(config, MemoryStore())

    def test_add_and_get_all(self):
        """测试添加记忆和获取所有记忆""" 
        # 添加记忆
        self.working_memory.add(MemoryItem(
            id=str(uuid.uuid4().hex),
            content="这是一个测试记忆1",
            memory_type="working",
            importance=0.5,
            timestamp=datetime.now(),
            metadata={"test": True}
        ))
        self.working_memory.add(MemoryItem(
            id=str(uuid.uuid4().hex),
            content="这是一个测试记忆2",
            memory_type="working",
            importance=0.5,
            timestamp=datetime.now(),
            metadata={"test": True}
        ))
        memory_id = self.working_memory.add(MemoryItem(
            id=str(uuid.uuid4().hex),
            content="你好啊",
            memory_type="working",
            importance=0.5,
            timestamp=datetime.now(),
            metadata={"test": True}
        ))
        # 检查记忆是否被添加
        all_memories = self.working_memory.get_all()
        self.assertEqual(len(all_memories), 3)
        self.assertEqual(all_memories[-1].id, memory_id)
        self.assertEqual(all_memories[0].content, "这是一个测试记忆1")

    def test_retrieve(self):
        """测试检索记忆功能"""
        # 添加多个记忆项
        test_contents = ["北京旅游攻略", "上海美食推荐", "广州购物指南", "深圳科技景点"]
        
        for i, content in enumerate(test_contents):
            memory_item = MemoryItem(
                id=str(uuid.uuid4().hex),
                content=content,
                memory_type="working",
                importance=0.5 + i * 0.1,
                timestamp=datetime.now(),
                metadata={"category": "travel" if i % 2 == 0 else "food"}
            )
            self.working_memory.add(memory_item)
        
        # 检索与"旅游"相关的记忆
        retrieved = self.working_memory.retrieve("旅游、美食", limit=5)

        # 应该至少包含"北京旅游攻略"
        self.assertGreaterEqual(len(retrieved), 2)
        found = any("旅游" in mem.content for mem in retrieved)
        self.assertTrue(found)

    def test_update_memory(self):
        """测试更新记忆功能"""
        # 添加一个记忆
        original_memory = MemoryItem(
            id=str(uuid.uuid4()),
            content="原始内容",
            memory_type="working",
            importance=0.3,
            timestamp=datetime.now(),
            metadata={"original": True}
        )
        memory_id = self.working_memory.add(original_memory)
        
        # 更新记忆
        success = self.working_memory.update(
            memory_id=memory_id,
            content="更新后的内容",
            importance=0.8,
            metadata={"updated": True}
        )
        
        # 验证更新是否成功
        self.assertTrue(success)
        
        all_memories = self.working_memory.get_all()
        updated_memory = all_memories[0]
        self.assertEqual(updated_memory.content, "更新后的内容")
        self.assertIn("updated", updated_memory.metadata)
        
    def test_remove_memory(self):
        """测试删除记忆功能"""
        # 添加一个记忆
        memory_item = MemoryItem(
            id=str(uuid.uuid4()),
            content="待删除的记忆",
            memory_type="working",
            importance=0.5,
            timestamp=datetime.now(),
            metadata={}
        )
        memory_id = self.working_memory.add(memory_item)
        
        # 验证记忆已添加
        all_memories = self.working_memory.get_all()
        self.assertEqual(len(all_memories), 1)
        
        # 删除记忆
        success = self.working_memory.remove(memory_id)
        self.assertTrue(success)
        
        # 验证记忆已被删除
        all_memories_after = self.working_memory.get_all()
        self.assertEqual(len(all_memories_after), 0)

    def test_has_memory(self):
        """测试检查记忆是否存在"""
        # 添加一个记忆
        memory_item = MemoryItem(
            id=str(uuid.uuid4()),
            content="测试记忆",
            memory_type="working",
            importance=0.5,
            timestamp=datetime.now(),
            metadata={}
        )
        memory_id = self.working_memory.add(memory_item)
        
        # 检查记忆是否存在
        self.assertTrue(self.working_memory.has_memory(memory_id))
        
        # 检查不存在的记忆
        fake_id = str(uuid.uuid4().hex)
        self.assertFalse(self.working_memory.has_memory(fake_id))

    def test_clear_memory(self):
        """测试清空所有记忆"""
        # 添加多个记忆
        for i in range(3):
            memory_item = MemoryItem(
                id=str(uuid.uuid4()),
                content=f"记忆 {i}",
                memory_type="working",
                importance=0.5,
                timestamp=datetime.now(),
                metadata={}
            )
            self.working_memory.add(memory_item)
        
        # 验证记忆已添加
        all_memories = self.working_memory.get_all()
        self.assertEqual(len(all_memories), 3)
        
        # 清空记忆
        self.working_memory.clear()
        
        # 验证记忆已被清空
        all_memories_after = self.working_memory.get_all()
        self.assertEqual(len(all_memories_after), 0)

    def test_get_stats(self):
        """测试获取统计信息"""
        # 添加一些记忆
        for i in range(3):
            memory_item = MemoryItem(
                id=str(uuid.uuid4()),
                content=f"记忆 {i}",
                memory_type="working",
                importance=0.5 + i * 0.1,
                timestamp=datetime.now(),
                metadata={}
            )
            self.working_memory.add(memory_item)
        
        # 获取统计信息
        stats = self.working_memory.get_stats()
        
        # 验证统计信息
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["memory_type"], "working")
        self.assertGreaterEqual(stats["avg_importance"], 0.5)

    def test_get_recent(self):
        """测试获取最近的记忆"""
        # 添加多个记忆，带不同的时间戳
        base_time = datetime.now() - timedelta(minutes=10)
        
        for i in range(3):
            current_time = base_time + timedelta(minutes=i)
            memory_item = MemoryItem(
                id=str(uuid.uuid4()),
                content=f"记忆 {i}",
                memory_type="working",
                importance=0.5,
                timestamp=current_time,
                metadata={}
            )
            self.working_memory.add(memory_item)
        
        # 获取最近的记忆
        recent_memories = self.working_memory.get_recent(limit=5)
        # 验证最近的记忆按时间倒序排列
        self.assertEqual(len(recent_memories), 3)
        for i in range(len(recent_memories) - 1):
            self.assertGreaterEqual(recent_memories[i].timestamp, recent_memories[i+1].timestamp)

    def test_get_important(self):
        """测试获取重要的记忆"""
        # 添加多个具有不同重要性的记忆
        importances = [0.3, 0.8, 0.5, 0.9, 0.1]
        
        for i, imp in enumerate(importances):
            memory_item = MemoryItem(
                id=str(uuid.uuid4()),
                content=f"重要记忆 {i}",
                memory_type="working",
                importance=imp,
                timestamp=datetime.now(),
                metadata={}
            )
            self.working_memory.add(memory_item)
        
        # 获取最重要的记忆
        important_memories = self.working_memory.get_important(limit=5)
        
        # 验证记忆按重要性降序排列
        self.assertEqual(len(important_memories), 5)
        for i in range(len(important_memories) - 1):
            self.assertGreaterEqual(important_memories[i].importance, important_memories[i+1].importance)

    def test_forget_mechanism(self):
        """测试遗忘机制"""
        # 添加多个记忆
        for i in range(5):
            memory_item = MemoryItem(
                id=str(uuid.uuid4()),
                content=f"记忆 {i}",
                memory_type="working",
                importance=0.1 if i < 3 else 0.8,  # 前三个重要性较低
                timestamp=datetime.now(),
                metadata={}
            )
            self.working_memory.add(memory_item)
        
        # 应用基于重要性的遗忘机制
        forgotten_count = self.working_memory.forget(strategy="importance_based", threshold=0.5)
        
        # 验证低重要性记忆被遗忘
        remaining_memories = self.working_memory.get_all()
        self.assertLessEqual(len(remaining_memories), 5)
        
        # 检查剩余的记忆都是高重要性的
        for memory in remaining_memories:
            self.assertGreaterEqual(memory.importance, 0.5)

    def test_capacity_limit_enforcement(self):
        """测试容量限制执行"""
        # 设置较小的容量限制
        config = MemoryConfig(
            enable_working=True,
            enable_semantic=False,
            enable_perceptual=False,
            enable_episodic=False,
            working_memory_capacity=3,  # 容量限制为3
            working_memory_tokens=100,
            working_memory_ttl=30
        )
        limited_memory = WorkingMemory(config, MemoryStore())
        
        # 添加超过容量限制的记忆
        for i in range(5):
            memory_item = MemoryItem(
                id=str(uuid.uuid4()),
                content=f"容量测试记忆 {i}",
                memory_type="working",
                importance=0.5 + i * 0.1,  # 后面的记忆更重要
                timestamp=datetime.now(),
                metadata={}
            )
            limited_memory.add(memory_item)
        
        # 检查是否只保留了容量限制内的记忆
        all_memories = limited_memory.get_all()
        self.assertLessEqual(len(all_memories), 3)


if __name__ == "__main__":
    unittest.main()
