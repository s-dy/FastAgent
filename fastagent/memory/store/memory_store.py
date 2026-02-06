from typing import List, Optional
import heapq

from fastagent.memory.base import BaseStore, MemoryItem


class MemoryStore(BaseStore):
    """基于内存存储"""
    def __init__(self,config:dict=None) -> None:
        if not config:
            config = {}
        super().__init__(config)

        # 内存存储
        self.memories: List[MemoryItem] = []
        # 使用优先级队列管理记忆
        self.memory_heap = []  # (priority, timestamp, memory_item)

    def list(self) -> List[MemoryItem]:
        return self.memories

    def get(self,memory_id:str) -> Optional[MemoryItem]:
        for memory in self.list():
            if memory.id == memory_id:
                return memory
        return None

    def add(self,memory_item:MemoryItem,**kwargs) -> None:
        priority: float = kwargs.get("priority",0)
        heapq.heappush(self.memory_heap, (-priority, memory_item.timestamp, memory_item))
        self.memories.append(memory_item)

    def clear(self) -> None:
        self.memories.clear()
        self.memory_heap.clear()

    def update(self,memory_item:MemoryItem,**kwargs) -> None:
        priority: float = kwargs.get("priority",0)
        for mem in self.memories:
            if mem.id == memory_item.id:
                mem.metadata = memory_item.metadata
                mem.timestamp = memory_item.timestamp
                mem.importance = priority
                heapq.heappush(self.memory_heap, (-priority, memory_item.timestamp, memory_item))
                return

    def remove(self,memory_id:str) -> None:
        for i,mem in enumerate(self.memories):
            if mem.id == memory_id:
                self.memories.pop(i)
