import unittest
import time
import numpy as np
from unittest.mock import patch

from src.memory.store.milvus_store import MilvusVectorStore, MilvusConnectionManager


class TestMilvusVectorStore(unittest.TestCase):
    """Milvus向量存储测试类"""

    def setUp(self):
        """测试前准备"""
        # 测试配置
        self.test_config = {
            'host': 'localhost',
            'port': 19530,
            'collection_name': 'test_fast_agents_vectors',
            'vector_size': 128,
            'metric_type': 'IP'
        }
        
        # 创建存储实例
        self.store = MilvusVectorStore(**self.test_config)
        
        # 测试向量数据
        self.test_vectors = [
            [0.1] * 128,  # 128维向量
            [0.2] * 128,
            [0.3] * 128
        ]
        
        self.test_metadata = [
            {
                "memory_type": "observation",
                "user_id": "test_user_1",
                "memory_id": "mem_001",
                "timestamp": int(time.time()),
                "modality": "text",
                "source": "test",
                "external": False
            },
            {
                "memory_type": "reflection",
                "user_id": "test_user_1",
                "memory_id": "mem_002",
                "timestamp": int(time.time()),
                "modality": "text",
                "source": "test",
                "external": True
            },
            {
                "memory_type": "observation",
                "user_id": "test_user_2",
                "memory_id": "mem_003",
                "timestamp": int(time.time()),
                "modality": "image",
                "source": "test",
                "external": False
            }
        ]

    def tearDown(self):
        """测试后清理"""
        try:
            # 清空测试集合
            self.store.clear_collection()
            # 释放资源
            if hasattr(self.store, 'collection') and self.store.collection:
                self.store.collection.release()
        except:
            pass

    def test_singleton_pattern(self):
        """测试单例模式"""
        # 使用相同配置创建第二个实例
        store2 = MilvusVectorStore(**self.test_config)
        
        # 应该是同一个实例（通过连接管理器）
        manager1 = MilvusConnectionManager.get_instance(**self.test_config)
        manager2 = MilvusConnectionManager.get_instance(**self.test_config)
        self.assertIs(manager1, manager2)

    def test_add_vectors(self):
        """测试添加向量"""
        # 添加向量
        success = self.store.add_vectors(self.test_vectors, self.test_metadata)
        
        # 验证添加成功
        self.assertTrue(success)
        
        # 验证集合中有数据
        info = self.store.get_collection_info()
        self.assertGreater(info.get("entities_count", 0), 0)

    def test_add_vectors_empty(self):
        """测试添加空向量列表"""
        success = self.store.add_vectors([], [])
        self.assertFalse(success)

    def test_add_vectors_dimension_mismatch(self):
        """测试向量维度不匹配"""
        # 创建维度不匹配的向量
        wrong_dim_vectors = [[0.1] * 64]  # 64维而不是128维
        metadata = [{"test": "data"}]
        
        success = self.store.add_vectors(wrong_dim_vectors, metadata)
        self.assertFalse(success)

    def test_search_similar(self):
        """测试相似向量搜索"""
        # 先添加测试数据
        self.store.add_vectors(self.test_vectors, self.test_metadata)
        
        # 使用第一个向量作为查询向量
        query_vector = self.test_vectors[0]
        
        # 搜索相似向量
        results = self.store.search_similar(query_vector, limit=5)
        
        # 验证返回结果
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        
        # 验证结果格式
        for result in results:
            self.assertIn("id", result)
            self.assertIn("score", result)
            self.assertIn("metadata", result)
            self.assertIsInstance(result["metadata"], dict)

    def test_search_similar_with_filter(self):
        """测试带过滤条件的相似搜索"""
        # 先添加测试数据
        self.store.add_vectors(self.test_vectors, self.test_metadata)
        
        # 使用查询向量
        query_vector = self.test_vectors[0]
        
        # 按用户ID过滤
        results = self.store.search_similar(
            query_vector,
            limit=5,
            where={"user_id": "test_user_1"}
        )
        
        # 验证过滤结果
        self.assertIsInstance(results, list)
        if results:  # 如果有结果
            for result in results:
                self.assertEqual(result["metadata"]["user_id"], "test_user_1")

    def test_search_similar_with_score_threshold(self):
        """测试带分数阈值的相似搜索"""
        # 先添加测试数据
        self.store.add_vectors(self.test_vectors, self.test_metadata)
        
        # 使用查询向量
        query_vector = self.test_vectors[0]
        
        # 设置高阈值（应该返回较少结果）
        results = self.store.search_similar(
            query_vector,
            limit=10,
            score_threshold=0.9
        )
        
        # 验证结果数量
        self.assertIsInstance(results, list)
        # 由于是相同向量查询，应该至少有一个高分结果
        if results:
            self.assertGreaterEqual(results[0]["score"], 0.9)

    def test_search_similar_wrong_dimension(self):
        """测试查询向量维度错误"""
        # 使用错误维度的查询向量
        wrong_vector = [0.1] * 64  # 64维而不是128维
        
        results = self.store.search_similar(wrong_vector, limit=5)
        
        # 应该返回空列表
        self.assertEqual(results, [])

    def test_delete_vectors(self):
        """测试删除向量"""
        # 先添加测试数据
        self.store.add_vectors(self.test_vectors, self.test_metadata)
        
        # 获取一些向量ID进行删除测试
        query_vector = self.test_vectors[0]
        results = self.store.search_similar(query_vector, limit=2)
        
        if results:
            # 提取要删除的ID
            delete_ids = [str(result["id"]) for result in results[:1]]  # 删除第一个
            
            # 执行删除
            success = self.store.delete_vectors(delete_ids)
            self.assertTrue(success)

    def test_delete_memories(self):
        """测试删除指定记忆"""
        # 先添加测试数据
        self.store.add_vectors(self.test_vectors, self.test_metadata)
        
        # 删除特定memory_id的记忆
        memory_ids_to_delete = ["mem_001"]
        self.store.delete_memories(memory_ids_to_delete)
        
        # 验证删除后的搜索结果
        query_vector = self.test_vectors[0]
        results = self.store.search_similar(
            query_vector, 
            limit=10, 
            where={"memory_id": "mem_001"}
        )
        
        # 应该找不到被删除的记忆
        self.assertEqual(len(results), 0)

    def test_clear_collection(self):
        """测试清空集合"""
        # 先添加测试数据
        self.store.add_vectors(self.test_vectors, self.test_metadata)
        
        # 清空集合
        success = self.store.clear_collection()
        self.assertTrue(success)
        
        # 验证集合已清空
        info = self.store.get_collection_info()
        self.assertEqual(info.get("entities_count", 1), 0)

    def test_get_collection_info(self):
        """测试获取集合信息"""
        info = self.store.get_collection_info()
        
        # 验证基本信息
        self.assertIn("name", info)
        self.assertIn("entities_count", info)
        self.assertIn("vector_size", info)
        self.assertIn("metric_type", info)
        self.assertIn("index_type", info)
        
        self.assertEqual(info["name"], self.test_config["collection_name"])
        self.assertEqual(info["vector_size"], self.test_config["vector_size"])
        self.assertEqual(info["metric_type"], self.test_config["metric_type"])

    def test_get_collection_stats(self):
        """测试获取集合统计信息"""
        stats = self.store.get_collection_stats()
        
        # 验证统计信息格式
        self.assertIn("store_type", stats)
        self.assertIn("name", stats)
        self.assertEqual(stats["store_type"], "milvus")
        self.assertEqual(stats["name"], self.test_config["collection_name"])

    def test_multiple_operations(self):
        """测试多个操作的组合使用"""
        # 1. 添加向量
        success = self.store.add_vectors(self.test_vectors, self.test_metadata)
        self.assertTrue(success)
        
        # 2. 搜索
        query_vector = self.test_vectors[0]
        results = self.store.search_similar(query_vector, limit=3)
        self.assertGreater(len(results), 0)
        
        # 3. 删除部分数据
        if results:
            delete_ids = [str(results[0]["id"])]
            self.store.delete_vectors(delete_ids)
        
        # 4. 再次搜索验证
        new_results = self.store.search_similar(query_vector, limit=3)
        self.assertLessEqual(len(new_results), len(results))

    @patch('src.memory.store.milvus_store.connections.connect')
    def test_connection_failure(self, mock_connect):
        """测试连接失败情况"""
        # 模拟连接失败
        mock_connect.side_effect = Exception("连接失败")
        
        # 应该抛出异常
        with self.assertRaises(Exception):
            MilvusVectorStore(
                host='invalid_host',
                port=9999,
                collection_name='test_collection',
                vector_size=128
            )

    def test_thread_safety(self):
        """测试线程安全性"""
        import concurrent.futures
        
        def add_test_vectors(thread_id: int):
            vectors = [[float(thread_id + i)/100.0] * 128 for i in range(2)]
            metadata = [
                {
                    "memory_type": "thread_test",
                    "user_id": f"user_{thread_id}",
                    "memory_id": f"mem_{thread_id}_{i}",
                    "timestamp": int(time.time())
                }
                for i in range(2)
            ]
            return self.store.add_vectors(vectors, metadata)
        
        # 使用线程池并发添加向量
        thread_count = 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(add_test_vectors, i) for i in range(thread_count)]
            
            # 等待所有任务完成
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
        # 验证所有操作都成功
        self.assertTrue(all(results))

    def test_large_scale_operations(self):
        """测试大规模操作"""
        # 创建大量测试数据
        large_vectors = []
        large_metadata = []
        
        for i in range(50):  # 50个向量
            vector = np.random.rand(128).tolist()  # 随机128维向量
            metadata = {
                "memory_type": "large_test",
                "user_id": f"user_{i % 5}",  # 5个不同用户
                "memory_id": f"large_mem_{i}",
                "timestamp": int(time.time()),
                "modality": "text" if i % 2 == 0 else "image"
            }
            large_vectors.append(vector)
            large_metadata.append(metadata)
        
        # 添加大量数据
        success = self.store.add_vectors(large_vectors, large_metadata)
        self.assertTrue(success)
        
        # 验证数据已添加
        info = self.store.get_collection_info()
        self.assertGreaterEqual(info.get("entities_count", 0), 50)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)