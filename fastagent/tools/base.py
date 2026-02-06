from abc import ABC,abstractmethod
from typing import Any, Dict

from pydantic import BaseModel


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


def _map_parameter_type(param_type: str) -> str:
    """将工具参数类型映射为JSON Schema允许的类型"""
    normalized = (param_type or "").lower()
    if normalized in {"string", "number", "integer", "boolean", "array", "object"}:
        return normalized
    return "string"


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
            prop:dict[str,Any] = {
                "type": _map_parameter_type(param.type),
                "description": param.description,
            }
            if param.default is not None:
                prop["description"] = f"{param.description}"
            if param.default is not None:
                prop["default"] = param.default
            # 如果是数组类型，添加 items 定义
            if param.type == 'array':
                # 默认字符串数组
                prop["items"] = {"type": "string"}
            
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

    def convert_parameter_types(self, param_dict: dict[str, Any]) -> dict[str, Any]:
        """根据工具定义尽可能转换参数类型"""
        try:
            tool_params = self.get_parameters()
        except Exception:
            return param_dict

        type_mapping = {param.name: param.type for param in tool_params}
        converted: dict[str, Any] = {}

        for key, value in param_dict.items():
            param_type = type_mapping.get(key)
            if not param_type:
                converted[key] = value
                continue

            try:
                normalized = param_type.lower()
                if normalized in {"number", "float"}:
                    converted[key] = float(value)
                elif normalized in {"integer", "int"}:
                    converted[key] = int(value)
                elif normalized in {"boolean", "bool"}:
                    if isinstance(value, bool):
                        converted[key] = value
                    elif isinstance(value, (int, float)):
                        converted[key] = bool(value)
                    elif isinstance(value, str):
                        converted[key] = value.lower() in {"true", "1", "yes"}
                    else:
                        converted[key] = bool(value)
                else:
                    converted[key] = value
            except (TypeError, ValueError):
                converted[key] = value

        return converted


    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [param.dict() for param in self.get_parameters()]
        }

    def __str__(self) -> str:
        return f"Tool(name={self.name})"

    def __repr__(self) -> str:
        return self.__str__()