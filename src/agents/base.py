from abc import ABC, abstractmethod
from typing import Optional

from src.core.llm import LLM
from src.core.config import Config
from src.core.message import Message


class Agent(ABC):
    """Base class for all agents."""
    def __init__(
        self,
        name: str,
        llm: LLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None
    ) -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []
    
    @abstractmethod
    def run(self,input_text: str, **kwargs) -> str:
        """Run the agent with the given input text."""
        raise NotImplementedError
    
    def add_message(self, message: Message) -> None:
        """Add a message to the history."""
        self._history.append(message)
    
    def clear_history(self) -> None:
        """Clear the history."""
        self._history = []

    def get_history(self) -> list[Message]:
        """Get the history."""
        return self._history
    
    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
