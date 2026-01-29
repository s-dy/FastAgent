from src.memory.config import MemoryConfig
from src.memory.tool import MemoryTool

user_id = "test_user"
session_id = "test_1111"
config = MemoryConfig(enable_working=True,enable_episodic=False,enable_semantic=False,enable_perceptual=False)
memory_tool = MemoryTool(session_id, user_id=user_id, config=config)

# add memory
print(memory_tool.run({
    'action': 'add',
    "content": "memory1",
    "memory_type": "working",
    "importance": 0.5,
    "metadata": {},
}))
print(memory_tool.run({
    'action': 'add',
    "content": "memory2",
    "memory_type": "working",
    "importance": 0.7,
    "metadata": {},
}))
print(memory_tool.run({
    'action': 'add',
    "content": "memory3",
    "memory_type": "working",
    "importance": 0.2,
    "metadata": {},
}))

search_result = memory_tool.run({
    'action': 'search',
    "query": "memory",
    "memory_types": ["working"],
    "min_importance":  0.1,
})
print(search_result)