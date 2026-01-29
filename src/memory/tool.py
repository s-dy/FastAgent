from datetime import datetime
from typing import List

from src.memory.manager import MemoryManager
from src.memory.config import MemoryConfig



class MemoryTool:
    def __init__(self,current_session_id:str, user_id="default_user", config:MemoryConfig=None) -> None:
        self.current_session_id = current_session_id
        self.memory_manager = MemoryManager(user_id=user_id, config=config or MemoryConfig())

    def execute(self,action:str,**kwargs):
        """执行记忆操作

        支持的操作：
        - add: 添加记忆（支持4种类型: working/episodic/semantic/perceptual）
        - search: 搜索记忆
        - summary: 获取记忆摘要
        - update: 更新记忆
        - remove: 删除记忆
        - forget: 遗忘记忆（多种策略）
        - consolidate: 整合记忆（短期→长期）
        - clear_all: 清空所有记忆
        """
        if action == "add":
            return self._add_memory(**kwargs)
        elif action == "search":
            return self._search_memory(**kwargs)
        elif action == "summary":
            return self._get_summary(**kwargs)
        elif action == "update":
            return self._update_memory(**kwargs)
        elif action == "remove":
            return self._remove_memory(**kwargs)
        elif action == "forget":
            return self._forget_memory(**kwargs)
        elif action == "consolidate":
            return self._consolidate_memory(**kwargs)
        elif action == "clear_all":
            return self._clear_all_memory()
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def run(self,task:dict):
        """运行记忆任务"""
        try:
            action = task.pop("action")
            return self.execute(action=action,**task)
        except Exception as e:
            raise "action is Required"

    def _get_current_session_id(self) -> str:
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _infer_modality(self, file_path: str) -> str:
        return "image" if file_path.endswith((".png", ".jpg", ".jpeg", ".gif")) else "text" if file_path.endswith((".txt", ".md")) else "unknown" if file_path else "none"

    def _add_memory(
        self,
        content: str = "",
        memory_type: str = "working",
        importance: float = 0.5,
        file_path: str = None,
        modality: str = None,
        metadata: dict = None,
    ) -> str:
        """添加记忆"""
        try:
            # 确保会话ID存在
            if self.current_session_id is None:
                self.current_session_id = self._get_current_session_id()
            # 感知记忆文件支持
            if memory_type == "perceptual" and file_path:
                inferred = modality or self._infer_modality(file_path)
                metadata["modality"] = inferred
                metadata["raw_data"] = file_path
            # 添加会话信息到元数据
            metadata.update({
                "session_id": self.current_session_id,
                "memory_type": memory_type,
            })
            memory_id = self.memory_manager.add_memory(
                content=content,
                memory_type=memory_type,
                importance=importance,
                metadata=metadata,
            )
            return f"✅ 记忆已添加 (ID: {memory_id})"
        except Exception as e:
            return f"❌ 添加记忆失败: {str(e)}"

    def _search_memory(
        self,
        query: str,
        limit: int = 5,
        memory_types: List[str] = None,
        min_importance: float = 0.1
    ) -> str:
        """搜索记忆"""
        try:
            if not memory_types:
                memory_types = ['working']
            results = self.memory_manager.retrieve_memories(
                query=query,
                limit=limit,
                memory_types=memory_types,
                min_importance=min_importance
            )
            if not results:
                return f"🔍 未找到与 '{query}' 相关的记忆"

            formatted_results = [f"🔍 找到 {len(results)} 条相关记忆:"]

            for i, memory in enumerate(results, 1):
                memory_type_label = {
                    "working": "工作记忆",
                    "episodic": "情景记忆", 
                    "semantic": "语义记忆",
                    "perceptual": "感知记忆"
                }.get(memory.metadata.get('memory_type'), "未知类型记忆")

                formatted_results.append(
                    f"{i}. [{memory_type_label}] {memory.content} (重要性: {memory.importance:.2f})"
                )

            return "\n".join(formatted_results)

        except Exception as e:
            return f"❌ 搜索记忆失败: {str(e)}"

    def _forget_memory(self, strategy: str = "importance_based", threshold: float = 0.1, max_age_days: int = 30) -> str:
        """
        遗忘记忆（支持多种策略）
        - importance_based: 根据重要性遗忘
        - time_based: 根据时间遗忘
        - capacity_based: 当记忆数量超限时删除最不重要的
        """
        try:
            count = self.memory_manager.forget_memories(
                strategy=strategy,
                threshold=threshold,
                max_age_days=max_age_days
            )
            return f"🧹 已遗忘 {count} 条记忆（策略: {strategy}）"
        except Exception as e:
            return f"❌ 遗忘记忆失败: {str(e)}"

    def _consolidate_memory(self, from_type: str = "working", to_type: str = "episodic", importance_threshold: float = 0.7) -> str:
        """整合记忆（将重要的短期记忆提升为长期记忆）"""
        try:
            count = self.memory_manager.consolidate_memories(
                from_type=from_type,
                to_type=to_type,
                importance_threshold=importance_threshold,
            )
            return f"🔄 已整合 {count} 条记忆为长期记忆（{from_type} → {to_type}，阈值={importance_threshold}）"
        except Exception as e:
            return f"❌ 整合记忆失败: {str(e)}"

    def _get_summary(self,memory_types: list[str] = None) -> str:
        """获取记忆摘要"""
        try:
            if not memory_types:
                memory_types = ['working']
            summary = self.memory_manager.get_summary(memory_types)
            return f"📝 记忆摘要:\n{summary}"
        except Exception as e:
            return f"❌ 获取记忆摘要失败: {str(e)}"

    def _update_memory(
        self,
        memory_id: str,
        content: str = "",
        importance: float = 0.5,
        file_path: str = None,
        modality: str = None,
        metadata: dict = None,
    ) -> str:
        """更新记忆"""
        try:
            # 确保会话ID存在
            if self.current_session_id is None:
                raise ValueError("会话ID不存在")
            # 感知记忆文件支持
            if file_path:
                inferred = modality or self._infer_modality(file_path)
                metadata["modality"] = inferred
                metadata["raw_data"] = file_path

            memory_id = self.memory_manager.update_memory(
                memory_id=memory_id,
                content=content,
                importance=importance,
                metadata=metadata,
            )
            return f"✅ 记忆已更新 (ID: {memory_id})"
        except Exception as e:
            return f"❌ 更新记忆失败: {str(e)}"

    def _remove_memory(self, memory_id: str) -> str:
        """删除记忆"""
        try:
            self.memory_manager.remove_memory(memory_id)
            return f"✅ 记忆已删除 (ID: {memory_id})"
        except Exception as e:
            return f"❌ 删除记忆失败: {str(e)}"

    def _clear_all_memory(self) -> str:
        """清空所有记忆"""
        try:
            self.memory_manager.clear_all_memories()
            return "✅ 所有记忆已清空"
        except Exception as e:
            return f"❌ 清空记忆失败: {str(e)}"
