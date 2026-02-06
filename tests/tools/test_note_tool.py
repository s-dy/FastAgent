import unittest
import os
import tempfile
import shutil
from datetime import datetime
from fastagent.tools.builtin.note_tool import NoteTool

class TestNoteTool(unittest.TestCase):
    def setUp(self):
        """测试前准备：创建临时工作目录"""
        self.test_workspace = tempfile.mkdtemp()
        self.note_tool = NoteTool(workspace=self.test_workspace)
    
    def tearDown(self):
        """测试后清理：删除临时目录"""
        if os.path.exists(self.test_workspace):
            shutil.rmtree(self.test_workspace)
    
    def test_create_note(self):
        """测试创建笔记功能"""
        # 测试基本创建
        note_id = self.note_tool.run({
            "action": "create",
            "title": "测试笔记",
            "content": "这是测试内容",
            "note_type": "general",
            "tags": ["test", "unit"]
        })
        
        # 验证返回的note_id
        self.assertIsNotNone(note_id)
        self.assertTrue(note_id.startswith("note_"))
        
        # 验证索引中存在该笔记
        note_found = False
        for note in self.note_tool.notes_index["notes"]:
            if note["id"] == note_id:
                note_found = True
                self.assertEqual(note["title"], "测试笔记")
                self.assertEqual(note["type"], "general")
                self.assertEqual(note["tags"], ["test", "unit"])
                break
        self.assertTrue(note_found)
        
        # 验证文件已创建
        file_path = self.note_tool._get_note_path(note_id)
        self.assertTrue(os.path.exists(file_path))
    
    def test_read_note(self):
        """测试读取笔记功能"""
        # 先创建一个笔记
        note_id = self.note_tool.run({
            "action": "create",
            "title": "读取测试",
            "content": "读取测试内容",
            "note_type": "test"
        })
        
        # 读取笔记
        result = self.note_tool.run({
            "action": "read",
            "note_id": note_id
        })
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertIn("metadata", result)
        self.assertIn("content", result)
        self.assertEqual(result["content"], "读取测试内容")
        self.assertEqual(result["metadata"]["title"], "读取测试")
    
    def test_read_nonexistent_note(self):
        """测试读取不存在的笔记"""
        result = self.note_tool.run({
            "action": "read",
            "note_id": "nonexistent_note"
        })
        self.assertEqual(result, {})
    
    def test_update_note(self):
        """测试更新笔记功能"""
        # 创建笔记
        note_id = self.note_tool.run({
            "action": "create",
            "title": "原始标题",
            "content": "原始内容",
            "note_type": "general"
        })
        
        # 更新笔记
        result = self.note_tool.run({
            "action": "update",
            "note_id": note_id,
            "title": "更新后的标题",
            "content": "更新后的内容"
        })

        print(result)
        # 验证更新结果
        self.assertIn("更新成功", result)
        
        # 重新读取验证更新内容
        updated_note = self.note_tool.run({
            "action": "read",
            "note_id": note_id
        })
        
        self.assertEqual(updated_note["metadata"]["title"], "更新后的标题")
        self.assertEqual(updated_note["content"], "更新后的内容")
        # 验证更新时间已改变
        self.assertNotEqual(
            updated_note["metadata"]["updated_at"],
            updated_note["metadata"]["created_at"]
        )
    
    def test_update_partial_fields(self):
        """测试部分字段更新"""
        # 创建笔记
        note_id = self.note_tool.run({
            "action": "create",
            "title": "测试标题",
            "content": "测试内容",
            "note_type": "general"
        })
        
        # 只更新标题
        self.note_tool.run({
            "action": "update",
            "note_id": note_id,
            "title": "新标题"
        })
        
        # 验证只有标题被更新
        updated_note = self.note_tool.run({
            "action": "read",
            "note_id": note_id
        })
        
        self.assertEqual(updated_note["metadata"]["title"], "新标题")
        self.assertEqual(updated_note["content"], "测试内容")  # 内容应该保持不变
    
    def test_search_notes(self):
        """测试搜索笔记功能"""
        # 创建多个测试笔记
        note1_id = self.note_tool.run({
            "action": "create",
            "title": "Python学习笔记",
            "content": "今天学习了Python基础语法",
            "note_type": "study",
            "tags": ["python", "programming"]
        })
        
        note2_id = self.note_tool.run({
            "action": "create",
            "title": "Java开发心得",
            "content": "Java是一门面向对象的语言",
            "note_type": "study",
            "tags": ["java", "programming"]
        })
        
        # 搜索包含"Python"的笔记
        results = self.note_tool.run({
            "action": "search",
            "query": "Python"
        })
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], note1_id)
        
        # 搜索包含"编程"的笔记（通过标签）
        results = self.note_tool.run({
            "action": "search",
            "tags": ["programming"],
            "query": "语"
        })
        print(results)

        self.assertEqual(len(results), 2)
    
    def test_search_with_filters(self):
        """测试带过滤条件的搜索"""
        # 创建不同类型和标签的笔记
        note1_id = self.note_tool.run({
            "action": "create",
            "title": "工作笔记",
            "content": "工作任务记录",
            "note_type": "task_state",
            "tags": ["work"]
        })
        
        note2_id = self.note_tool.run({
            "action": "create",
            "title": "学习笔记",
            "content": "学习内容记录",
            "note_type": "study",
            "tags": ["study"]
        })
        
        # 按类型过滤
        results = self.note_tool.run({
            "action": "search",
            "query": "",
            "note_type": "task_state"
        })
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], note1_id)
        
        # 按标签过滤
        results = self.note_tool.run({
            "action": "search",
            "query": "",
            "tags": ["study"]
        })
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], note2_id)
    
    def test_delete_note(self):
        """测试删除笔记功能"""
        # 创建笔记
        note_id = self.note_tool.run({
            "action": "create",
            "title": "待删除笔记",
            "content": "这个笔记将被删除"
        })
        
        # 删除笔记
        result = self.note_tool.run({
            "action": "delete",
            "note_id": note_id
        })
        
        # 验证删除成功消息
        self.assertIn("已删除", result)
        
        # 验证索引中已删除
        note_found = False
        for note in self.note_tool.notes_index["notes"]:
            if note["id"] == note_id:
                note_found = True
                break
        self.assertFalse(note_found)
        
        # 验证文件已删除
        file_path = self.note_tool._get_note_path(note_id)
        self.assertFalse(os.path.exists(file_path))
    
    def test_delete_nonexistent_note(self):
        """测试删除不存在的笔记"""
        result = self.note_tool.run({
            "action": "delete",
            "note_id": "nonexistent_note"
        })
        self.assertIn("不存在", result)
    
    def test_list_notes(self):
        """测试列出笔记功能"""
        # 创建多个笔记
        note_ids = []
        for i in range(3):
            note_id = self.note_tool.run({
                "action": "create",
                "title": f"笔记{i+1}",
                "content": f"内容{i+1}",
                "note_type": "general" if i % 2 == 0 else "task_state"
            })
            note_ids.append(note_id)
        
        # 列出所有笔记
        results = self.note_tool.run({
            "action": "list"
        })
        
        self.assertEqual(len(results), 3)
        
        # 按类型过滤
        results = self.note_tool.run({
            "action": "list",
            "note_type": "task_state"
        })
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "task_state")
    
    def test_summary(self):
        """测试生成摘要功能"""
        # 创建不同类型笔记
        for i in range(5):
            self.note_tool.run({
                "action": "create",
                "title": f"笔记{i+1}",
                "content": f"内容{i+1}",
                "note_type": "general" if i < 3 else "task_state"
            })
        
        # 生成摘要
        summary = self.note_tool.run({
            "action": "summary"
        })
        
        # 验证摘要结构
        self.assertIn("total_count", summary)
        self.assertIn("type_distribution", summary)
        self.assertIn("recent_notes", summary)
        
        # 验证统计数据
        self.assertEqual(summary["total_count"], 5)
        self.assertEqual(summary["type_distribution"]["general"], 3)
        self.assertEqual(summary["type_distribution"]["task_state"], 2)
        self.assertEqual(len(summary["recent_notes"]), 5)
    
    def test_metadata_format(self):
        """测试元数据格式"""
        note_id = self.note_tool.run({
            "action": "create",
            "title": "元数据测试",
            "content": "测试元数据格式",
            "note_type": "test",
            "tags": ["meta", "test"]
        })
        
        note_data = self.note_tool.run({
            "action": "read",
            "note_id": note_id
        })
        
        metadata = note_data["metadata"]
        
        # 验证必需的元数据字段
        required_fields = ["id", "title", "type", "tags", "created_at", "updated_at"]
        for field in required_fields:
            self.assertIn(field, metadata)
        
        # 验证字段类型
        self.assertIsInstance(metadata["id"], str)
        self.assertIsInstance(metadata["title"], str)
        self.assertIsInstance(metadata["type"], str)
        self.assertIsInstance(metadata["tags"], list)
        self.assertIsInstance(metadata["created_at"], str)
        self.assertIsInstance(metadata["updated_at"], str)
        
        # 验证时间格式
        created_time = datetime.fromisoformat(metadata["created_at"])
        updated_time = datetime.fromisoformat(metadata["updated_at"])
        self.assertIsInstance(created_time, datetime)
        self.assertIsInstance(updated_time, datetime)

    def test_note_type_validation(self):
        """测试笔记类型验证"""
        # 测试有效的笔记类型
        valid_types = ["task_state", "conclusion", "blocker", "action", "reference", "general"]
        
        for note_type in valid_types:
            note_id = self.note_tool.run({
                "action": "create",
                "title": f"测试{note_type}",
                "content": "测试内容",
                "note_type": note_type
            })
            
            note_data = self.note_tool.run({
                "action": "read",
                "note_id": note_id
            })
            
            self.assertEqual(note_data["metadata"]["type"], note_type)

    def test_tags_handling(self):
        """测试标签处理功能"""
        # 测试创建带标签的笔记
        note_id = self.note_tool.run({
            "action": "create",
            "title": "标签测试",
            "content": "测试标签功能",
            "tags": ["tag1", "tag2", "tag3"]
        })
        
        note_data = self.note_tool.run({
            "action": "read",
            "note_id": note_id
        })
        
        self.assertEqual(set(note_data["metadata"]["tags"]), {"tag1", "tag2", "tag3"})
        
        # 测试更新标签
        self.note_tool.run({
            "action": "update",
            "note_id": note_id,
            "tags": ["new_tag1", "new_tag2"]
        })
        
        updated_note = self.note_tool.run({
            "action": "read",
            "note_id": note_id
        })
        
        self.assertEqual(set(updated_note["metadata"]["tags"]), {"new_tag1", "new_tag2"})

    def test_search_notes_case_insensitive(self):
        """测试搜索功能大小写不敏感"""
        # 创建包含大写字母的笔记
        note_id = self.note_tool.run({
            "action": "create",
            "title": "PYTHON学习笔记",
            "content": "Python是一种编程语言",
            "note_type": "study"
        })
        
        # 用小写搜索
        results = self.note_tool.run({
            "action": "search",
            "query": "python"
        })
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], note_id)

    def test_max_notes_limit(self):
        """测试笔记数量上限"""
        # 设置较小的上限进行测试
        limited_tool = NoteTool(workspace=tempfile.mkdtemp(), max_notes=2)
        
        # 创建达到上限的笔记
        for i in range(2):
            note_id = limited_tool.run({
                "action": "create",
                "title": f"笔记{i+1}",
                "content": f"内容{i+1}"
            })
            self.assertIsNotNone(note_id)
        
        # 尝试创建超过上限的笔记
        result = limited_tool.run({
            "action": "create",
            "title": "超出上限的笔记",
            "content": "这应该失败"
        })
        
        self.assertEqual(result, "")

if __name__ == '__main__':
    unittest.main()