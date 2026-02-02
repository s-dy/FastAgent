import unittest
import tempfile
import os
import shutil
from datetime import datetime, timedelta
import time

from src.memory.memory_types.episodic import EpisodicMemory
from src.memory.config import MemoryConfig
from src.memory.base import MemoryItem
from src.memory.store import PostGreStore, MilvusVectorStore,MemoryStore
from src.core.embeddings import EmbeddingConfig, create_embedding


class TestEpisodicMemoryReal(unittest.TestCase):
    """情景记忆真实环境测试（不使用mock）"""

    def setUp(self):
        """测试前置准备 - 使用真实组件"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()

        # 创建内存配置
        self.config = MemoryConfig(enable_episodic=True,enable_semantic=False,enable_perceptual=False,enable_working=True)

        # 创建PostgreSQL存储配置
        self.pg_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'fast_agent',
            'user': 'postgres',
            'password': '123456'
        }

        try:
            # 创建真实的存储后端
            self.doc_store = PostGreStore(self.pg_config)
            self.milvus_vector_store = MilvusVectorStore(vector_size=1024)

            # 创建真实的嵌入模型（使用轻量级模型）
            embedding_config = EmbeddingConfig(
                provider="ollama",
                model_name="qwen3-embedding:0.6B",
            )
            self.embedder = create_embedding(embedding_config)

            # 创建情景记忆实例
            self.episodic_memory = EpisodicMemory(self.config, MemoryStore(), self.doc_store, self.milvus_vector_store)
            # 替换嵌入器为真实嵌入器
            self.episodic_memory.embedder = self.embedder

        except Exception as e:
            self.skipTest(f"测试环境未准备好: {e}")

    def tearDown(self):
        """测试后清理"""
        # try:
        # 清空测试数据
        if hasattr(self, 'episodic_memory'):
            self.episodic_memory.clear()

        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # except Exception as e:
        #     print(f"清理测试环境时出错: {e}")

    def test_basic_memory_operations(self):
        """测试基本记忆操作"""
        # 测试添加记忆
        memory_item = MemoryItem(
            id="basic_test_1",
            content="用户询问今天的天气情况",
            memory_type="episodic",
            timestamp=datetime.now(),
            importance=0.8,
            metadata={
                "session_id": "session_basic",
                "user_id": "user_basic",
                "context": {"location": "北京", "time": "上午"},
                "outcome": "提供了详细的天气预报",
                "participants": ["user", "assistant"],
                "tags": ["weather", "inquiry", "morning"]
            }
        )

        # 添加记忆
        result_id = self.episodic_memory.add(memory_item)
        self.assertEqual(result_id, "basic_test_1")

        # 验证内部状态
        self.assertEqual(len(self.episodic_memory.episodes), 1)
        self.assertEqual(len(self.episodic_memory.sessions), 1)
        self.assertIn("session_basic", self.episodic_memory.sessions)

        # 测试记忆存在性检查
        self.assertTrue(self.episodic_memory.has_memory("basic_test_1"))
        self.assertFalse(self.episodic_memory.has_memory("nonexistent"))

    def test_memory_retrieval(self):
        """测试记忆检索功能"""
        # 添加多个测试记忆
        test_memories = [
            MemoryItem(
                id=f"retrieve_{i}",
                content=f"这是第{i}个测试记忆内容，包含一些关键词用于检索",
                memory_type="episodic",
                timestamp=datetime.now() - timedelta(minutes=i * 10),
                importance=0.5 + i * 0.1,
                metadata={
                    "session_id": "retrieve_session",
                    "user_id": "retrieve_user",
                    "context": {"category": f"category_{i}"},
                    "tags": [f"tag_{i}", "common_tag"]
                }
            ) for i in range(3)
        ]

        # 添加所有记忆
        for memory in test_memories:
            self.episodic_memory.add(memory)

        # 测试基本检索
        results = self.episodic_memory.retrieve("测试记忆", limit=2)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 2)

        # 测试带用户过滤的检索
        user_results = self.episodic_memory.retrieve(
            "测试",
            limit=5,
            user_id="retrieve_user"
        )
        self.assertGreater(len(user_results), 0)
        # 验证所有结果都属于指定用户
        for result in user_results:
            self.assertEqual(result.metadata.get("user_id"), "retrieve_user")

    def test_memory_update_and_remove(self):
        """测试记忆更新和删除"""
        # 添加初始记忆
        initial_memory = MemoryItem(
            id="update_remove_test",
            content="原始记忆内容",
            memory_type="episodic",
            timestamp=datetime.now(),
            importance=0.5,
            metadata={
                "session_id": "test_session",
                "user_id": "test_user",
                "context": {"status": "initial"}
            }
        )
        self.episodic_memory.add(initial_memory)

        # 测试更新功能
        update_success = self.episodic_memory.update(
            memory_id="update_remove_test",
            content="更新后的记忆内容",
            importance=0.9,
            metadata={"context": {"status": "updated", "modified": True}}
        )
        self.assertTrue(update_success)

        # 验证更新结果
        retrieved = self.episodic_memory.retrieve("更新后", limit=1)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0].content, "更新后的记忆内容")
        self.assertEqual(retrieved[0].importance, 0.9)
        self.assertTrue(retrieved[0].metadata.get("context", {}).get("modified"))

        # 测试删除功能
        delete_success = self.episodic_memory.remove("update_remove_test")
        self.assertTrue(delete_success)
        self.assertFalse(self.episodic_memory.has_memory("update_remove_test"))
        self.assertEqual(len(self.episodic_memory.episodes), 0)

    def test_session_management(self):
        """测试会话管理功能"""
        # 添加同一会话的多个记忆
        session_memories = []
        for i in range(3):
            memory = MemoryItem(
                id=f"session_test_{i}",
                content=f"会话{i}的内容",
                memory_type="episodic",
                timestamp=datetime.now() + timedelta(minutes=i),
                importance=0.5,
                metadata={
                    "session_id": "managed_session",
                    "user_id": "session_user",
                    "sequence": i
                }
            )
            self.episodic_memory.add(memory)
            session_memories.append(memory)

        # 测试获取会话情景
        session_episodes = self.episodic_memory.get_session_episodes("managed_session")
        self.assertEqual(len(session_episodes), 3)

        # 验证会话情景的正确性
        episode_ids = {ep.episode_id for ep in session_episodes}
        expected_ids = {f"session_test_{i}" for i in range(3)}
        self.assertEqual(episode_ids, expected_ids)

        # 测试不存在会话
        empty_episodes = self.episodic_memory.get_session_episodes("nonexistent_session")
        self.assertEqual(len(empty_episodes), 0)

    def test_forget_mechanism(self):
        """测试遗忘机制"""
        # 添加不同重要性的记忆
        low_importance_memory = MemoryItem(
            id="forget_low",
            content="低重要性记忆内容",
            memory_type="episodic",
            timestamp=datetime.now(),
            importance=0.1,  # 故意设得很低
            metadata={"session_id": "forget_session", "user_id": "forget_user"}
        )

        high_importance_memory = MemoryItem(
            id="forget_high",
            content="高重要性记忆内容",
            memory_type="episodic",
            timestamp=datetime.now(),
            importance=0.9,  # 故意设得很高
            metadata={"session_id": "forget_session", "user_id": "forget_user"}
        )

        self.episodic_memory.add(low_importance_memory)
        self.episodic_memory.add(high_importance_memory)

        # 基于重要性的遗忘测试
        forgotten_count = self.episodic_memory.forget(
            strategy="importance_based",
            threshold=0.5  # 阈值设为0.5，应该遗忘低重要性记忆
        )

        self.assertEqual(forgotten_count, 1)
        self.assertEqual(len(self.episodic_memory.episodes), 1)

        # 验证剩余的是高重要性记忆
        remaining_memory = self.episodic_memory.get_all()[0]
        self.assertEqual(remaining_memory.id, "forget_high")

    def test_statistics_and_patterns(self):
        """测试统计信息和模式发现"""
        # 添加测试数据
        for i in range(5):
            memory = MemoryItem(
                id=f"stats_pattern_{i}",
                content=f"统计测试内容 {i}，包含重复词汇用于模式分析",
                memory_type="episodic",
                timestamp=datetime.now() - timedelta(days=i),
                importance=0.3 + i * 0.1,
                metadata={
                    "session_id": f"session_{i % 2}",  # 创建2个会话
                    "user_id": "stats_user",
                    "category": "test_category"
                }
            )
            self.episodic_memory.add(memory)

        # 测试统计信息
        stats = self.episodic_memory.get_stats()
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["sessions_count"], 2)
        self.assertEqual(stats["memory_type"], "episodic")
        self.assertIn("avg_importance", stats)
        self.assertGreater(stats["time_span_days"], 0)

        # 测试模式发现
        patterns = self.episodic_memory.find_patterns(
            user_id="stats_user",
            min_frequency=2
        )
        print(patterns)
        self.assertIsInstance(patterns, list)
        # 验证找到了一些模式
        self.assertGreater(len(patterns), 0)

        # 检查是否包含预期的高频词汇模式
        keyword_patterns = [p for p in patterns if p["type"] == "keyword"]
        pattern_words = [p["pattern"] for p in keyword_patterns]
        # "统计"和"测试"应该是高频词
        common_words = ["统计", "测试"]
        found_common = [word for word in common_words if word in pattern_words]
        self.assertGreater(len(found_common), 0)

    def test_timeline_functionality(self):
        """测试时间线功能"""
        # 添加按时序排列的记忆
        timeline_memories = []
        base_time = datetime.now()
        for i in range(4):
            memory = MemoryItem(
                id=f"timeline_{i}",
                content=f"时间线测试内容 {i}",
                memory_type="episodic",
                timestamp=base_time - timedelta(hours=i),  # 倒序时间
                importance=0.5,
                metadata={
                    "session_id": f"timeline_session_{i}",
                    "user_id": "timeline_user",
                    "outcome": f"结果_{i}"
                }
            )
            self.episodic_memory.add(memory)
            timeline_memories.append(memory)

        # 获取时间线
        timeline = self.episodic_memory.get_timeline(
            user_id="timeline_user",
            limit=3
        )

        self.assertEqual(len(timeline), 3)
        # 验证时间顺序（应该是倒序）
        timestamps = [item["timestamp"] for item in timeline]
        sorted_timestamps = sorted(timestamps, reverse=True)
        self.assertEqual(timestamps, sorted_timestamps)

        # 验证时间线内容
        for item in timeline:
            self.assertIn("episode_id", item)
            self.assertIn("timestamp", item)
            self.assertIn("content", item)
            self.assertIn("session_id", item)

    def test_concurrent_operations(self):
        """测试并发操作"""
        import concurrent.futures

        def add_memory_thread(thread_id):
            memory = MemoryItem(
                id=f"concurrent_{thread_id}",
                content=f"并发线程{thread_id}添加的记忆",
                memory_type="episodic",
                timestamp=datetime.now(),
                importance=0.5,
                metadata={
                    "session_id": f"concurrent_session_{thread_id}",
                    "user_id": "concurrent_user"
                }
            )
            return self.episodic_memory.add(memory)

        # 使用线程池并发添加记忆
        thread_count = 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(add_memory_thread, i) for i in range(thread_count)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 验证所有操作都成功
        self.assertEqual(len(results), thread_count)
        self.assertEqual(len(self.episodic_memory.episodes), thread_count)

        # 验证所有记忆都能正确检索
        all_memories = self.episodic_memory.get_all()
        self.assertEqual(len(all_memories), thread_count)

    def test_large_scale_operations(self):
        """测试大规模操作"""
        # 添加大量记忆测试性能
        large_count = 20
        start_time = time.time()

        for i in range(large_count):
            memory = MemoryItem(
                id=f"large_scale_{i}",
                content=f"大规模测试内容 {i}，用于性能测试",
                memory_type="episodic",
                timestamp=datetime.now() - timedelta(minutes=i),
                importance=0.5,
                metadata={
                    "session_id": "large_session",
                    "user_id": "large_user",
                    "batch": "large_scale"
                }
            )
            self.episodic_memory.add(memory)

        add_time = time.time() - start_time
        print(f"添加{large_count}个记忆耗时: {add_time:.2f}秒")

        # 测试检索性能
        start_time = time.time()
        results = self.episodic_memory.retrieve("大规模测试", limit=10)
        search_time = time.time() - start_time
        print(f"检索耗时: {search_time:.2f}秒")

        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 10)

        # 验证统计数据
        stats = self.episodic_memory.get_stats()
        self.assertEqual(stats["count"], large_count)

    def test_error_handling(self):
        """测试错误处理"""
        # 测试添加重复ID的记忆
        memory1 = MemoryItem(
            id="duplicate_test",
            content="第一次添加",
            memory_type="episodic",
            timestamp=datetime.now(),
            importance=0.5,
            metadata={"session_id": "error_session", "user_id": "error_user"}
        )

        memory2 = MemoryItem(
            id="duplicate_test",  # 相同ID
            content="第二次添加",
            memory_type="episodic",
            timestamp=datetime.now(),
            importance=0.8,
            metadata={"session_id": "error_session", "user_id": "error_user"}
        )

        # 第一次应该成功
        result1 = self.episodic_memory.add(memory1)
        self.assertEqual(result1, "duplicate_test")

        # 第二次应该也能成功（更新操作）
        result2 = self.episodic_memory.add(memory2)
        self.assertEqual(result2, "duplicate_test")

        # 验证内容被更新
        retrieved = self.episodic_memory.retrieve("第二次添加", limit=1)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0].content, "第二次添加")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)