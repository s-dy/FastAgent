import unittest
import time
from unittest.mock import patch, MagicMock

from fastagent.memory.store.postgre_store import PostGreStore


class TestPostGreStore(unittest.TestCase):
    """PostgreSQL存储测试类"""

    def setUp(self):
        """测试前准备"""
        # 测试配置
        self.test_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'fast_agent',
            'user': 'postgres',
            'password': '123456'
        }
        
        # 创建存储实例
        self.store = PostGreStore(self.test_config)
        
        # 测试数据
        self.test_memory_id = "test_memory_001"
        self.test_user_id = "test_user_001"
        self.test_content = "这是一条测试记忆内容"
        self.test_memory_type = "test_type"
        self.test_timestamp = int(time.time())
        self.test_importance = 0.8
        self.test_properties = {
            "category": "test",
            "tags": ["important", "urgent"]
        }

    def tearDown(self):
        """测试后清理"""
        try:
            # 删除测试数据
            self.store.delete_memory(self.test_memory_id)
            # 关闭连接
            self.store.close()
        except:
            pass

    def test_singleton_pattern(self):
        """测试单例模式"""
        # 使用相同配置创建第二个实例
        store2 = PostGreStore(self.test_config)
        # 应该是同一个实例
        self.assertIs(self.store, store2)
        
        # 使用不同配置创建实例
        different_config = self.test_config.copy()
        different_config['database'] = 'hybridragsystem'
        store3 = PostGreStore(different_config)
        
        # 应该是不同的实例
        self.assertIsNot(self.store, store3)

    def test_add_memory(self):
        """测试添加记忆"""
        # 添加记忆
        result_id = self.store.add_memory(
            memory_id=self.test_memory_id,
            user_id=self.test_user_id,
            content=self.test_content,
            memory_type=self.test_memory_type,
            timestamp=self.test_timestamp,
            importance=self.test_importance,
            properties=self.test_properties
        )
        
        # 验证返回的ID
        self.assertEqual(result_id, self.test_memory_id)
        
        # 验证记忆已存在
        memory = self.store.get_memory(self.test_memory_id)
        self.assertIsNotNone(memory)
        self.assertEqual(memory["memory_id"], self.test_memory_id)
        self.assertEqual(memory["user_id"], self.test_user_id)
        self.assertEqual(memory["content"], self.test_content)
        self.assertEqual(memory["memory_type"], self.test_memory_type)
        self.assertEqual(memory["timestamp"], self.test_timestamp)
        self.assertEqual(memory["importance"], self.test_importance)
        self.assertEqual(memory["properties"], self.test_properties)

    def test_get_memory_not_exists(self):
        """测试获取不存在的记忆"""
        memory = self.store.get_memory("non_existent_id")
        self.assertIsNone(memory)

    def test_search_memories(self):
        """测试搜索记忆"""
        # 先添加几条测试数据
        test_memories = [
            {
                "id": "search_test_1",
                "user_id": "user1",
                "content": "第一条测试记忆",
                "type": "observation",
                "timestamp": int(time.time()) - 1000,
                "importance": 0.5
            },
            {
                "id": "search_test_2",
                "user_id": "user1",
                "content": "第二条测试记忆",
                "type": "reflection",
                "timestamp": int(time.time()) - 500,
                "importance": 0.8
            },
            {
                "id": "search_test_3",
                "user_id": "user2",
                "content": "第三条测试记忆",
                "type": "observation",
                "timestamp": int(time.time()),
                "importance": 0.3
            }
        ]
        
        # 添加测试数据
        for mem in test_memories:
            self.store.add_memory(
                memory_id=mem["id"],
                user_id=mem["user_id"],
                content=mem["content"],
                memory_type=mem["type"],
                timestamp=mem["timestamp"],
                importance=mem["importance"]
            )
        
        try:
            # 测试按用户ID搜索
            results = self.store.search_memories(user_id="user1")
            self.assertEqual(len(results), 2)
            self.assertTrue(all(mem["user_id"] == "user1" for mem in results))
            
            # 测试按记忆类型搜索
            results = self.store.search_memories(memory_type="observation")
            self.assertEqual(len(results), 2)
            self.assertTrue(all(mem["memory_type"] == "observation" for mem in results))
            
            # 测试按重要性阈值搜索
            results = self.store.search_memories(importance_threshold=0.6)
            self.assertEqual(len(results), 1)
            self.assertTrue(all(mem["importance"] >= 0.6 for mem in results))
            
            # 测试限制返回数量
            results = self.store.search_memories(limit=1)
            self.assertEqual(len(results), 1)
            
            # 测试组合条件搜索
            results = self.store.search_memories(
                user_id="user1",
                memory_type="observation"
            )
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["memory_id"], "search_test_1")
            
        finally:
            # 清理测试数据
            for mem in test_memories:
                self.store.delete_memory(mem["id"])

    def test_update_memory(self):
        """测试更新记忆"""
        # 先添加记忆
        self.store.add_memory(
            memory_id=self.test_memory_id,
            user_id=self.test_user_id,
            content=self.test_content,
            memory_type=self.test_memory_type,
            timestamp=self.test_timestamp,
            importance=self.test_importance,
            properties=self.test_properties
        )
        
        # 更新内容和重要性
        new_content = "更新后的记忆内容"
        new_importance = 0.9
        
        success = self.store.update_memory(
            memory_id=self.test_memory_id,
            content=new_content,
            importance=new_importance
        )
        
        self.assertTrue(success)
        
        # 验证更新结果
        updated_memory = self.store.get_memory(self.test_memory_id)
        self.assertEqual(updated_memory["content"], new_content)
        self.assertEqual(updated_memory["importance"], new_importance)
        # 其他字段应该保持不变
        self.assertEqual(updated_memory["memory_type"], self.test_memory_type)
        self.assertEqual(updated_memory["user_id"], self.test_user_id)

    def test_update_memory_partial(self):
        """测试部分更新记忆"""
        # 先添加记忆
        self.store.add_memory(
            memory_id=self.test_memory_id,
            user_id=self.test_user_id,
            content=self.test_content,
            memory_type=self.test_memory_type,
            timestamp=self.test_timestamp,
            importance=self.test_importance
        )
        
        # 只更新内容
        new_content = "只更新内容"
        success = self.store.update_memory(
            memory_id=self.test_memory_id,
            content=new_content
        )
        
        self.assertTrue(success)
        
        # 验证只有内容被更新
        updated_memory = self.store.get_memory(self.test_memory_id)
        self.assertEqual(updated_memory["content"], new_content)
        self.assertEqual(updated_memory["importance"], self.test_importance)  # 应该保持原值

    def test_update_memory_not_exists(self):
        """测试更新不存在的记忆"""
        success = self.store.update_memory(
            memory_id="non_existent_id",
            content="新内容"
        )
        self.assertFalse(success)

    def test_delete_memory(self):
        """测试删除记忆"""
        # 先添加记忆
        self.store.add_memory(
            memory_id=self.test_memory_id,
            user_id=self.test_user_id,
            content=self.test_content,
            memory_type=self.test_memory_type,
            timestamp=self.test_timestamp,
            importance=self.test_importance
        )
        
        # 删除记忆
        success = self.store.delete_memory(self.test_memory_id)
        self.assertTrue(success)
        
        # 验证记忆已被删除
        memory = self.store.get_memory(self.test_memory_id)
        self.assertIsNone(memory)

    def test_delete_memory_not_exists(self):
        """测试删除不存在的记忆"""
        success = self.store.delete_memory("non_existent_id")
        self.assertFalse(success)  # PostgreSQL DELETE不会报错，但rowcount为0

    def test_add_document(self):
        """测试添加文档"""
        test_content = "这是一个测试文档内容"
        test_metadata = {
            "user_id": "doc_user",
            "title": "测试文档",
            "category": "test"
        }
        
        # 添加文档
        doc_id = self.store.add_document(test_content, test_metadata)
        
        # 验证文档已添加
        document = self.store.get_document(doc_id)
        print(document)
        self.assertIsNotNone(document)
        self.assertEqual(document["content"], test_content)
        self.assertEqual(document["memory_type"], "document")
        self.assertEqual(document["properties"], test_metadata)
        
        # 清理
        self.store.delete_memory(doc_id)

    def test_get_database_stats(self):
        """测试获取数据库统计信息"""
        # 先添加一些测试数据
        test_data = [
            ("stats_test_1", "user1", "内容1", "observation", 0.5),
            ("stats_test_2", "user1", "内容2", "reflection", 0.8),
            ("stats_test_3", "user2", "内容3", "observation", 0.3),
        ]
        
        for mem_id, user_id, content, mem_type, importance in test_data:
            self.store.add_memory(
                memory_id=mem_id,
                user_id=user_id,
                content=content,
                memory_type=mem_type,
                timestamp=int(time.time()),
                importance=importance
            )
        
        try:
            # 获取统计信息
            stats = self.store.get_database_stats()
            
            # 验证基本字段
            self.assertIn("store_type", stats)
            self.assertIn("users_count", stats)
            self.assertIn("memories_count", stats)
            self.assertIn("memory_types", stats)
            self.assertEqual(stats["store_type"], "postgresql")
            
            # 验证记忆类型统计
            self.assertIn("observation", stats["memory_types"])
            self.assertIn("reflection", stats["memory_types"])
            
        finally:
            # 清理测试数据
            for mem_id, _, _, _, _ in test_data:
                self.store.delete_memory(mem_id)

    def test_thread_safety(self):
        """测试线程安全性"""
        import threading
        import concurrent.futures
        
        def add_test_memory(thread_id: int):
            memory_id = f"thread_test_{thread_id}"
            self.store.add_memory(
                memory_id=memory_id,
                user_id=f"user_{thread_id}",
                content=f"线程{thread_id}的测试内容",
                memory_type="thread_test",
                timestamp=int(time.time()),
                importance=0.5
            )
            return memory_id
        
        # 使用线程池并发添加记忆
        thread_count = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            future_to_thread = {
                executor.submit(add_test_memory, i): i 
                for i in range(thread_count)
            }
            
            # 收集结果
            added_ids = []
            for future in concurrent.futures.as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    memory_id = future.result()
                    added_ids.append(memory_id)
                except Exception as exc:
                    print(f'线程 {thread_id} 产生异常: {exc}')
        
        try:
            # 验证所有记忆都被正确添加
            for memory_id in added_ids:
                memory = self.store.get_memory(memory_id)
                self.assertIsNotNone(memory)
                self.assertTrue(memory_id.startswith("thread_test_"))
        finally:
            # 清理测试数据
            for memory_id in added_ids:
                self.store.delete_memory(memory_id)

    def test_json_properties_handling(self):
        """测试JSON属性处理"""
        # 测试复杂的JSON属性
        complex_properties = {
            "nested_dict": {
                "key1": "value1",
                "key2": [1, 2, 3]
            },
            "list_of_dicts": [
                {"name": "item1", "value": 10},
                {"name": "item2", "value": 20}
            ],
            "boolean_flag": True,
            "null_value": None
        }
        
        # 添加带有复杂属性的记忆
        self.store.add_memory(
            memory_id=self.test_memory_id,
            user_id=self.test_user_id,
            content=self.test_content,
            memory_type=self.test_memory_type,
            timestamp=self.test_timestamp,
            importance=self.test_importance,
            properties=complex_properties
        )
        
        # 验证属性被正确存储和检索
        memory = self.store.get_memory(self.test_memory_id)
        self.assertEqual(memory["properties"], complex_properties)

    @patch('src.memory.store.postgre_store.psycopg2.connect')
    def test_connection_failure(self, mock_connect):
        """测试连接失败情况"""
        # 模拟连接失败
        mock_connect.side_effect = Exception("连接失败")
        
        # 应该抛出异常
        with self.assertRaises(Exception):
            PostGreStore({
                'host': 'invalid_host',
                'port': 9999,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_pass'
            })


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)