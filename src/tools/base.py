from abc import ABC,abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class Tool(ABC):
    """Base class for all tools."""
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
    
    @abstractmethod
    def run(self, parameters: dict) -> str:
        """Run the tool."""
        raise NotImplementedError

    @abstractmethod
    def get_parameters(self) -> list[ToolParameter]:
        """Get the parameters for the tool."""
        raise NotImplementedError
    
    def to_openai_schema(self) -> dict:
        """转换为 OpenAI function calling schema 格式

        用于 FunctionCallAgent，使工具能够被 OpenAI 原生 function calling 使用

        Returns:
            符合 OpenAI function calling 标准的 schema
        """
        parameters = self.get_parameters()

        properties = {}
        required = []

        for param in parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            # 如果有默认值，添加到描述中（OpenAI schema 不支持 default 字段）
            if param.default is not None:
                prop["description"] = f"{param.description} (默认: {param.default})"
            # 如果是数组类型，添加 items 定义
            if param.type == 'array':
                # 默认字符串数组
                prop["items"] = {"type": "stirng"}
            
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        }