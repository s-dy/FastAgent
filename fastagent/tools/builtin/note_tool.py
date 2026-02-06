"""
NoteTool 是为"长时程任务"提供的结构化外部记忆组件。它以 Markdown 文件作为载体，头部使用 YAML 前置元数据记录关键信息，正文用于记录状态、结论、阻塞与行动项等内容。
这种设计结合了人类可读性、版本控制友好性和易于回注上下文的特性，是构建长时程智能体的重要工具。
"""
import json
from pathlib import Path

from fastagent.tools.base import Tool, ToolParameter

"""NoteTool - 结构化笔记工具

为Agent提供结构化笔记能力，支持：
- 创建/读取/更新/删除笔记
- 按类型组织（任务状态、结论、阻塞项、行动计划等）
- 持久化存储（Markdown格式，带YAML前置元数据）
- 搜索与过滤
- 与MemoryTool集成（可选）

使用场景：
- 长时程任务的状态跟踪
- 关键结论与依赖记录
- 待办事项与行动计划
- 项目知识沉淀

笔记格式示例：
```markdown
---
id: note_20250118_120000_0
title: 项目进展
type: task_state
tags: [milestone, phase1]
created_at: 2025-01-18T12:00:00
updated_at: 2025-01-18T12:00:00
---

# 项目进展

已完成需求分析，下一步：设计方案

## 关键里程碑
- [x] 需求收集
- [ ] 方案设计
```
"""
import yaml
from typing import Optional, List
from datetime import datetime

from fastagent.monitor import monitor_task_status


class NoteTool(Tool):
    """笔记工具

    为Agent提供结构化笔记管理能力，支持多种笔记类型：
    - task_state: 任务状态
    - conclusion: 关键结论
    - blocker: 阻塞项
    - action: 行动计划
    - reference: 参考资料
    - general: 通用笔记
    """
    def __init__(self, workspace:str,max_notes: int = 1000):
        super().__init__(
            name="note",
            description="笔记工具 - 创建、读取、更新、删除结构化笔记，支持任务状态、结论、阻塞项等类型"
        )
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.max_notes = max_notes
        self.index_file = self.workspace / "notes_index.json"
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.notes_index = json.load(f)
        else:
            self.notes_index = {
                "notes": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "total_notes": 0
                }
            }
            self._save_index()

    def _save_index(self):
        if self.index_file.exists():
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.notes_index, f, ensure_ascii=False, indent=2)

    def _generate_note_id(self) -> str:
        """生成笔记ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        count = len(self.notes_index["notes"])
        return f"note_{timestamp}_{count}"

    def _get_note_path(self, note_id: str) -> Path:
        """获取笔记文件路径"""
        return self.workspace / f"{note_id}.md"

    def run(self,task:dict):
        try:
            action = task.pop("action")
            if action == "create":
                return self._create_note(**task)
            elif action == "read":
                return self._read_note(**task)
            elif action == "update":
                return self._update_note(**task)
            elif action == "search":
                return self._search_notes(**task)
            elif action == "delete":
                return self._delete_note(**task)
            elif action == "list":
                return self._list_notes(**task)
            elif action == "summary":
                return self._summary(**task)
            else:
                monitor_task_status(f"❌ 不支持的操作: {action}")
        except Exception as e:
            print(e)

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description=(
                    "操作类型: create(创建), read(读取), update(更新), "
                    "delete(删除), list(列表), search(搜索), summary(摘要)"
                ),
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="笔记标题（create/update时必需）",
                required=False
            ),
            ToolParameter(
                name="content",
                type="string",
                description="笔记内容（create/update时必需）",
                required=False
            ),
            ToolParameter(
                name="note_type",
                type="string",
                description=(
                    "笔记类型: task_state(任务状态), conclusion(结论), "
                    "blocker(阻塞项), action(行动计划), reference(参考), general(通用)"
                ),
                required=False,
                default="general"
            ),
            ToolParameter(
                name="tags",
                type="array",
                description="标签列表（可选）",
                required=False
            ),
            ToolParameter(
                name="note_id",
                type="string",
                description="笔记ID（read/update/delete时必需）",
                required=False
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词（search时必需）",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回结果数量限制（默认10）",
                required=False,
                default=10
            ),
        ]

    def _create_note(
        self,
        title: str,
        content: str,
        note_type: str = "general",
        tags: Optional[list[str]] = None
    ) -> str:
        """创建笔记

        Args:
            title: 笔记标题
            content: 笔记内容(Markdown格式)
            note_type: 笔记类型(task_state/conclusion/blocker/action/reference/general)
            tags: 标签列表

        Returns:
            str: 笔记ID
        """
        if len(self.notes_index["notes"]) >= self.max_notes:
             monitor_task_status(f"❌ 笔记数量已达上限 ({self.max_notes})",level="WARNING")
             return ""

        note_id = self._generate_note_id()

        # 构建元数据
        metadata = {
            "id": note_id, # 笔记ID
            "title": title, # 标题  
            "type": note_type, # 类型
            "tags": tags or [], # 标签列表  
            "created_at": datetime.now().isoformat(), # 创建时间    
            "updated_at": datetime.now().isoformat(), # 更新时间
            "status": "active"
        }

        md_content = self._build_markdown(metadata, content)
        note_path = self._get_note_path(note_id)
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        self.notes_index["notes"].append(metadata)
        self.notes_index["metadata"]["total_notes"] = len(self.notes_index["notes"])
        self._save_index()

        monitor_task_status(f"✅ 笔记创建成功\nID: {note_id}\n标题: {title}\n类型: {note_type}")
        return note_id
    
    def _build_markdown(self, metadata:dict, content:str) -> str:
        """构建 Markdown 文件内容(YAML + 正文)"""
        yaml_header = yaml.dump(metadata, allow_unicode=True,sort_keys=False)
        return f"---\n{yaml_header}---\n\n{content}"

    def _read_note(self, note_id: str,format_note:bool=False) -> dict | str:
        """读取笔记内容

        Args:
            note_id: 笔记ID
            format_note: 是否结构化输出

        Returns:
            Dict: 包含元数据和内容的字典
        """
        note_path = self._get_note_path(note_id)
        if not note_path.exists():
            monitor_task_status(f"❌ 笔记不存在: {note_id}", level="WARNING")
            return {}
        with open(note_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        metadata,content = self._parse_markdown(raw_content)
        if format_note:
            return self._format_note(metadata, content)

        return {
            "metadata": metadata,
            "content": content
        }
    
    def _parse_markdown(self, raw_content: str) -> tuple[dict, str]:
        """解析 Markdown 文件内容( YAML + 正文)"""
        parts = raw_content.split("---\n",2)
        if len(parts) >= 3:
            yaml_str = parts[1]
            metadata = yaml.safe_load(yaml_str)
            content = parts[2].strip()
        else:
            metadata = {}
            content = raw_content.strip()
        return metadata, content

    def _format_note(self, metadata:dict, content:str) -> str:
        """格式化笔记输出"""
        result = f"📝 笔记详情\n\n"
        result += f"ID: {metadata['id']}\n"
        result += f"标题: {metadata['title']}\n"
        result += f"类型: {metadata['type']}\n"
        if metadata.get('tags'):
            result += f"标签: {', '.join(metadata['tags'])}\n"
        result += f"创建时间: {metadata['created_at']}\n"
        result += f"更新时间: {metadata['updated_at']}\n"
        result += f"\n内容:\n{content}\n"
        return result

    def _update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        note_type: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> str:
        """更新笔记

        Args:
            note_id: 笔记ID
            title: 新标题(可选)
            content: 新内容(可选)
            note_type: 新类型(可选)
            tags: 新标签(可选)

        Returns:
            str: 操作结果消息
        """
        note_path = self._get_note_path(note_id)
        if not note_path.exists():
            return f"❌ 笔记不存在: {note_id}"

        note:dict = self._read_note(note_id)
        metadata, old_content = note["metadata"], note["content"]

        if title:
            metadata["title"] = title
        if note_type:
            metadata["type"] = note_type
        if tags is not None:
            metadata["tags"] = tags
        if content is not None:
            old_content = content
        
        metadata["updated_at"] = datetime.now().isoformat()

        md_content = self._build_markdown(metadata, old_content)
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # 更新索引
        for idx_note in self.notes_index["notes"]:
            if idx_note["id"] == note_id:
                idx_note["title"] = metadata["title"]
                idx_note["type"] = metadata["type"]
                idx_note["tags"] = metadata["tags"]
                break
        self._save_index()
        return f"✅ 笔记更新成功: {note_id}"

    def _search_notes(
        self,
        query: str,
        limit: int = 10,
        note_type: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> list[dict]:
        """搜索笔记

        Args:
            query: 搜索关键词
            limit: 返回数量限制
            note_type: 按类型过滤(可选)
            tags: 按标签过滤(可选)

        Returns:
            List[Dict]: 匹配的笔记列表
        """
        results = []
        query_lower = query.lower()
        for note_data in self.notes_index["notes"]:
            if note_type and note_data["type"] != note_type:
                continue
            
            if tags:
                note_tags = set(note_data.get("tags", []))
                if not note_tags.issuperset(tags):
                    continue
            
            note = self._read_note(note_data['id'])
            content = note["content"]
            if query_lower in note_data["title"].lower() or query_lower in content.lower():
                results.append({
                    "content": content,
                    **note["metadata"],
                })

        results.sort(key=lambda x: x["updated_at"], reverse=True)
        return results[:limit]

    def _delete_note(self, note_id: str) -> str:
        """删除笔记

        Args:
            note_id: 笔记ID

        Returns:
            str: 操作结果消息
        """
        note_path = self._get_note_path(note_id)
        if not note_path.exists():
            return f"❌ 笔记不存在: {note_id}"

        # 删除文件
        note_path.unlink()
        # 更新索引
        self.notes_index["notes"] = [
            n for n in self.notes_index["notes"] if n["id"] != note_id
        ]
        self.notes_index["metadata"]["total_notes"] = len(self.notes_index["notes"])
        self._save_index()

        return f"✅ 笔记已删除: {note_id}"

    def _list_notes(
        self,
        note_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 10
    ) -> list[dict]:
        """列出笔记

        Args:
            note_type: 按类型过滤(可选)
            tags: 按标签过滤(可选)
            limit: 返回数量限制

        Returns:
            List[Dict]: 笔记列表
        """
        results = []
        for note in self.notes_index["notes"]:
            if note_type and note["type"] != note_type:
                continue
            
            if tags:
                note_tags = set(note.get("tags", []))
                if not note_tags.issuperset(tags):
                    continue
            
            results.append(note)
        
        results.sort(key=lambda x: x["updated_at"], reverse=True)
        return results[:limit]

    def _summary(self,**kwargs) -> dict:
        """生成笔记摘要

        Returns:
            Dict: 笔记摘要
        """
        total = len(self.notes_index["notes"])

        type_counts = {}
        for note in self.notes_index["notes"]:
            note_type = note.get("type","general")
            type_counts[note_type] = type_counts.get(note_type, 0) + 1

        # 最近更新的笔记
        recent_notes = sorted(self.notes_index["notes"], key=lambda x: x["updated_at"], reverse=True)[:10]

        return {
            "total_count": total,
            "type_distribution": type_counts,
            "recent_notes": [
                {
                    "id": note["id"],
                    "title": note.get("title", ""),
                    "type": note.get("type"),
                    "updated_at": note.get("updated_at")
                }
                for note in recent_notes
            ]
        }