from abc import ABC, abstractmethod
from typing import Optional,List

from fastagent.core import LLMClient, Config, Message


class MessageState:
    """消息状态管理类"""

    def __init__(self, messages: List[Message] = None):
        self.messages: List[Message] = messages or []

    def add_message(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)

    def clear(self) -> None:
        """清空所有消息"""
        self.messages.clear()

    def get_messages(self) -> List[Message]:
        """获取所有消息"""
        return self.messages.copy()

    def get_latest_message(self) -> Optional[Message]:
        """获取最新消息"""
        return self.messages[-1] if self.messages else None

    def get_message_count(self) -> int:
        """获取消息总数"""
        return len(self.messages)

    def get_dict_messages(self) -> list[dict]:
        """获取结构化后的数据"""
        result = []
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result


class Agent(ABC):
    """Base class for all agents."""
    def __init__(
        self,
        name: str,
        llm: LLMClient,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None
    ) -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()

    @abstractmethod
    def run(self,input_text: str, **kwargs) -> str:
        """Run the agent with the given input text."""
        raise NotImplementedError
    
    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
    
    def __repr__(self) -> str:
        return self.__str__()
