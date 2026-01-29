from typing import List

from src.memory.base import BaseStore, MemoryItem


class MemoryStore(BaseStore):
    """基于内存存储"""
    def __init__(self,config:dict=None) -> None:
        if not config:
            config = {}
        super().__init__(config)
        self.memories = {}  # user -> memories

    def list(self, user_id: str) -> List[MemoryItem]:
        return self.memories.get(user_id, [])

    def add(self,user_id:str, memory_item:MemoryItem) -> None:
        if user_id not in self.memories:
            self.memories[user_id] = []
        self.memories[user_id].append(memory_item)