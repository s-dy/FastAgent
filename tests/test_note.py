import os

from src.context.note import NoteTool

if __name__ == '__main__':
    workspace = "./project_notes"
    if not os.path.exists(workspace):
        os.makedirs(workspace)
    notes = NoteTool(workspace=workspace)

    ### 创建
    note_id = notes.run({
        "action": "create",
        "title": "重构项目 - 第一阶段",
        "content": """## 完成情况
    已完成数据模型层的重构,测试覆盖率达到85%。

    ## 下一步
    重构业务逻辑层""",
        "note_type": "task_state",
        "tags": ["refactoring", "phase1"]
    })

    print(f"✅ 笔记创建成功,ID: {note_id}")
    ### 读取
    note = notes.run({
        "action": "read",
        "note_id": note_id,
    })
    print(note)

    ### 更新
    notes.run({
        "action": "update",
        "note_id": note_id,
        "title": "重构项目 - 第二阶段",
        "content": """## 完成。

    ## 下一步
    重构业务逻辑层""",
        "note_type": "task_state",
        "tags": ["refactoring", "phase1"]
    })
    print(f"✅ 笔记更新成功")

    note = notes.run({
        "action": "read",
        "note_id": note_id,
    })
    print(note)

    ### list
    notes_list = notes.run({
        "action": "list",
        "note_type": "task_state",
        "tags": ["refactoring", "phase1"]
    })
    print(f"✅ 笔记列表获取成功")
    print(notes_list)

    ### summary
    summary = notes.run({
        "action": "summary",
    })
    print(f"✅ 笔记摘要获取成功")
    print(summary)

    ### 删除
    notes.run({
        "action": "delete",
        "note_id": note_id,
    })
    print(f"✅ 笔记删除成功")

    note = notes.run({
        "action": "read",
        "note_id": note_id,
    })
    print(note)

