from typing import List, Dict, Any, Optional
import psycopg2
import json
import threading
import uuid
import time

from fastagent.monitor import monitor_task_status
from fastagent.memory.base import BaseDocumentStore


class PostGreStore(BaseDocumentStore):
    """PostgreSQL存储实现"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.local = threading.local()  # 隔离不同线程的连接，避免并发问题

        super().__init__(config)

    def _get_connection(self):
        """获取线程本地连接"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = psycopg2.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 5432),
                database=self.config.get('database', 'fast_agent'),
                user=self.config.get('user', 'postgres'),
                password=self.config.get('password', '')
            )
        return self.local.connection

    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                properties JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                timestamp BIGINT NOT NULL,
                importance REAL NOT NULL,
                properties JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 创建概念表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                properties JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建记忆-概念关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_concepts (
                memory_id TEXT NOT NULL,
                concept_id TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (memory_id, concept_id),
                FOREIGN KEY (memory_id) REFERENCES memories (id) ON DELETE CASCADE,
                FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE CASCADE
            )
        """)

        # 创建概念关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concept_relationships (
                from_concept_id TEXT NOT NULL,
                to_concept_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                properties JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (from_concept_id, to_concept_id, relationship_type),
                FOREIGN KEY (from_concept_id) REFERENCES concepts (id) ON DELETE CASCADE,
                FOREIGN KEY (to_concept_id) REFERENCES concepts (id) ON DELETE CASCADE
            )
        """)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories (memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories (importance)",
            "CREATE INDEX IF NOT EXISTS idx_memory_concepts_memory ON memory_concepts (memory_id)",
            "CREATE INDEX IF NOT EXISTS idx_memory_concepts_concept ON memory_concepts (concept_id)"
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        conn.commit()
        monitor_task_status("[OK] PostgreSQL 数据库表和索引创建完成")

    def add_memory(
            self,
            memory_id: str,
            user_id: str,
            content: str,
            memory_type: str,
            timestamp: int,
            importance: float,
            properties: Dict[str, Any] = None
    ) -> str:
        """添加记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 确保用户存在
        cursor.execute(
            "INSERT INTO users (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (user_id, user_id)
        )

        # 插入记忆
        cursor.execute("""
            INSERT INTO memories 
            (id, user_id, content, memory_type, timestamp, importance, properties, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                memory_type = EXCLUDED.memory_type,
                timestamp = EXCLUDED.timestamp,
                importance = EXCLUDED.importance,
                properties = EXCLUDED.properties,
                updated_at = CURRENT_TIMESTAMP
        """, (
            memory_id,
            user_id,
            content,
            memory_type,
            timestamp,
            importance,
            json.dumps(properties) if properties else None
        ))

        conn.commit()
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取单个记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, content, memory_type, timestamp, importance, properties, created_at
            FROM memories
            WHERE id = %s
        """, (memory_id,))

        row = cursor.fetchone()
        if not row:
            return None
        return {
            "memory_id": row[0],
            "user_id": row[1],
            "content": row[2],
            "memory_type": row[3],
            "timestamp": row[4],
            "importance": row[5],
            "properties": row[6] if row[6] else {},
            "created_at": row[7]
        }

    def search_memories(
            self,
            user_id: Optional[str] = None,
            memory_type: Optional[str] = None,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None,
            importance_threshold: Optional[float] = None,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 构建查询条件
        where_conditions = []
        params = []

        if user_id:
            where_conditions.append("user_id = %s")
            params.append(user_id)

        if memory_type:
            where_conditions.append("memory_type = %s")
            params.append(memory_type)

        if start_time:
            where_conditions.append("timestamp >= %s")
            params.append(start_time)

        if end_time:
            where_conditions.append("timestamp <= %s")
            params.append(end_time)

        if importance_threshold:
            where_conditions.append("importance >= %s")
            params.append(importance_threshold)

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        cursor.execute(f"""
            SELECT id, user_id, content, memory_type, timestamp, importance, properties, created_at
            FROM memories
            {where_clause}
            ORDER BY importance DESC, timestamp DESC
            LIMIT %s
        """, params + [limit])

        memories = []
        for row in cursor.fetchall():
            memories.append({
                "memory_id": row[0],
                "user_id": row[1],
                "content": row[2],
                "memory_type": row[3],
                "timestamp": row[4],
                "importance": row[5],
                "properties": row[6],
                "created_at": row[7]
            })

        return memories

    def update_memory(
            self,
            memory_id: str,
            content: str = None,
            importance: float = None,
            properties: Dict[str, Any] = None
    ) -> bool:
        """更新记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 构建更新字段
        update_fields = []
        params = []

        if content is not None:
            update_fields.append("content = %s")
            params.append(content)

        if importance is not None:
            update_fields.append("importance = %s")
            params.append(importance)

        if properties is not None:
            update_fields.append("properties = %s")
            params.append(json.dumps(properties))

        if not update_fields:
            return False

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(memory_id)

        cursor.execute(f"""
            UPDATE memories
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return cursor.rowcount > 0

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
        deleted_count = cursor.rowcount

        conn.commit()
        return deleted_count > 0

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}

        # 统计各表的记录数
        tables = ["users", "memories", "concepts", "memory_concepts", "concept_relationships"]
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]

        # 统计记忆类型分布
        cursor.execute("""
            SELECT memory_type, COUNT(*) as count
            FROM memories
            GROUP BY memory_type
        """)
        memory_types = {}
        for row in cursor.fetchall():
            memory_types[row[0]] = row[1]
        stats["memory_types"] = memory_types

        # 统计用户分布
        cursor.execute("""
            SELECT user_id, COUNT(*) as count
            FROM memories
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
        """)
        top_users = {}
        for row in cursor.fetchall():
            top_users[row[0]] = row[1]
        stats["top_users"] = top_users

        stats["store_type"] = "postgresql"
        stats["config"] = self.config

        return stats

    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加文档"""
        doc_id = self._generate_id()
        user_id = metadata.get("user_id", "system") if metadata else "system"

        return self.add_memory(
            memory_id=doc_id,
            user_id=user_id,
            content=content,
            memory_type="document",
            timestamp=int(time.time()),
            importance=0.5,
            properties=metadata or {}
        )

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档"""
        return self.get_memory(document_id)

    def close(self):
        """关闭数据库连接"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            delattr(self.local, 'connection')
            monitor_task_status("[OK] PostgreSQL 连接已关闭")

    def _generate_id(self):
        return str(uuid.uuid4().hex)