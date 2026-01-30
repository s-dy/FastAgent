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
    
    @abstractmethod
    def run(self,input_text: str, **kwargs) -> str:
        """Run the agent with the given input text."""
        raise NotImplementedError
    
    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
    
    def __repr__(self) -> str:
        return self.__str__()
