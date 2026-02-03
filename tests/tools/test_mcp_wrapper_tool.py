import asyncio
import unittest
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.tools.builtin import MCPWrappedTool, MCPTool


class TestMCPWrappedToolInitialization(unittest.TestCase):
    """MCP包装工具初始化测试"""

    def setUp(self):
        """测试前置准备"""
        # 创建mock的父MCP工具
        self.mock_mcp_tool = Mock(spec=MCPTool)
        self.mock_mcp_tool.run = Mock(return_value="Mock result")
        
        # 测试工具信息
        self.tool_info = {
            "name": "calculator",
            "description": "计算数学表达式",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式"
                    }
                },
                "required": ["expression"]
            }
        }

    def test_basic_initialization(self):
        """测试基本初始化"""
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=self.tool_info
        )
        
        self.assertEqual(wrapped_tool.name, "calculator")
        self.assertEqual(wrapped_tool.description, "计算数学表达式")
        self.assertEqual(wrapped_tool.mcp_tool_name, "calculator")
        self.assertEqual(wrapped_tool.mcp_tool, self.mock_mcp_tool)

    def test_initialization_with_prefix(self):
        """测试带前缀的初始化"""
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=self.tool_info,
            prefix="math_"
        )
        
        self.assertEqual(wrapped_tool.name, "math_calculator")
        self.assertEqual(wrapped_tool.mcp_tool_name, "calculator")

    def test_initialization_missing_name(self):
        """测试缺少名称的情况"""
        tool_info_no_name = {
            "description": "测试工具",
            "input_schema": {}
        }
        
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=tool_info_no_name
        )
        
        self.assertEqual(wrapped_tool.name, "unknown")
        self.assertEqual(wrapped_tool.mcp_tool_name, "unknown")


class TestMCPWrappedToolParameterParsing(unittest.TestCase):
    """MCP包装工具参数解析测试"""

    def setUp(self):
        """测试前置准备"""
        self.mock_mcp_tool = Mock(spec=MCPTool)
        self.simple_tool_info = {
            "name": "simple_tool",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "消息内容"
                    }
                }
            }
        }

    def test_parse_simple_schema(self):
        """测试解析简单schema"""
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=self.simple_tool_info
        )
        
        parameters = wrapped_tool.get_parameters()
        
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters[0].name, "message")
        self.assertEqual(parameters[0].type, "string")
        self.assertEqual(parameters[0].description, "消息内容")
        self.assertFalse(parameters[0].required)  # 不在required列表中

    def test_parse_schema_with_required_fields(self):
        """测试解析带必需字段的schema"""
        tool_info_with_required = {
            "name": "required_tool",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "用户名"
                    },
                    "age": {
                        "type": "integer",
                        "description": "年龄"
                    }
                },
                "required": ["name"]  # name是必需的
            }
        }
        
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=tool_info_with_required
        )
        
        parameters = wrapped_tool.get_parameters()
        
        # 找到name参数
        name_param = next(p for p in parameters if p.name == "name")
        age_param = next(p for p in parameters if p.name == "age")
        
        self.assertTrue(name_param.required)
        self.assertFalse(age_param.required)

    def test_parse_empty_schema(self):
        """测试解析空schema"""
        tool_info_empty = {
            "name": "empty_tool",
            "input_schema": {}
        }
        
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=tool_info_empty
        )
        
        parameters = wrapped_tool.get_parameters()
        self.assertEqual(len(parameters), 0)

    def test_parse_complex_schema(self):
        """测试解析复杂schema"""
        tool_info_complex = {
            "name": "complex_tool",
            "input_schema": {
                "type": "object",
                "properties": {
                    "config": {
                        "type": "object",
                        "description": "配置对象",
                        "properties": {
                            "timeout": {"type": "integer"},
                            "retry": {"type": "boolean"}
                        }
                    },
                    "tags": {
                        "type": "array",
                        "description": "标签数组",
                        "items": {"type": "string"}
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "是否启用"
                    }
                },
                "required": ["config", "enabled"]
            }
        }
        
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=tool_info_complex
        )
        
        parameters = wrapped_tool.get_parameters()
        
        self.assertEqual(len(parameters), 3)
        
        # 验证各参数类型
        param_dict = {p.name: p for p in parameters}
        self.assertEqual(param_dict["config"].type, "object")
        self.assertEqual(param_dict["tags"].type, "array")
        self.assertEqual(param_dict["enabled"].type, "boolean")
        
        # 验证必需字段
        self.assertTrue(param_dict["config"].required)
        self.assertTrue(param_dict["enabled"].required)
        self.assertFalse(param_dict["tags"].required)


class TestMCPWrappedToolExecution(unittest.TestCase):
    """MCP包装工具执行测试"""

    def setUp(self):
        """测试前置准备"""
        self.mock_mcp_tool = Mock(spec=MCPTool)
        self.tool_info = {
            "name": "test_tool",
            "description": "测试工具",
            "input_schema": {}
        }

    def test_run_method_calls_parent(self):
        """测试run方法调用父工具"""
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=self.tool_info
        )
        
        # 执行工具
        test_params = {"param1": "value1", "param2": "value2"}
        result = wrapped_tool.run(test_params)
        print(result)
        # 验证父工具被正确调用
        self.mock_mcp_tool.run.assert_called_once_with({
            "action": "call_tool",
            "tool_name": "test_tool",
            "arguments": test_params
        })

    def test_run_with_empty_parameters(self):
        """测试运行时空参数"""
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=self.tool_info
        )
        
        result = wrapped_tool.run({})
        
        self.mock_mcp_tool.run.assert_called_once_with({
            "action": "call_tool",
            "tool_name": "test_tool",
            "arguments": {}
        })

    def test_run_with_nested_parameters(self):
        """测试运行嵌套参数"""
        wrapped_tool = MCPWrappedTool(
            mcp_tool=self.mock_mcp_tool,
            tool_info=self.tool_info
        )
        
        nested_params = {
            "config": {"timeout": 30, "retry": True},
            "data": [1, 2, 3, 4]
        }
        result = wrapped_tool.run(nested_params)
        
        self.mock_mcp_tool.run.assert_called_once_with({
            "action": "call_tool",
            "tool_name": "test_tool",
            "arguments": nested_params
        })


class TestMCPWrappedToolIntegration(unittest.TestCase):
    """MCP包装工具集成测试"""

    @patch('src.protocols.mcp.client.MCPClient')
    @patch('utils.async_event.run_async_event')
    def test_wrapper_with_real_mcp_tool(self, mock_run_async, mock_mcp_client):
        """测试包装工具与真实MCP工具的集成"""
        # Mock MCP客户端
        mock_client_instance = Mock()
        mock_client_instance.list_tools = Mock(return_value=[
            {
                "name": "calculator",
                "description": "计算工具",
                "input_schema": {
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式"
                        }
                    },
                    "required": ["expression"]
                }
            }
        ])
        mock_mcp_client.return_value = mock_client_instance
        
        # Mock异步执行
        async def mock_operation():
            return "Result: 42"
        mock_run_async.return_value = asyncio.run(mock_operation())

        # 创建真实的MCP工具
        mcp_tool = MCPTool(name="math", server_command=["python", "/Users/sdy/TravelAgent/tests/protocols/mcp/server.py"])
        
        # 创建包装工具
        tool_info = {
            "name": "calculator",
            "description": "计算工具",
            "input_schema": {
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式"
                    }
                },
                "required": ["expression"]
            }
        }
        
        wrapped_tool = MCPWrappedTool(
            mcp_tool=mcp_tool,
            tool_info=tool_info
        )
        
        # 测试参数获取
        parameters = wrapped_tool.get_parameters()
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters[0].name, "expression")
        self.assertTrue(parameters[0].required)
        
        # 测试执行
        result = wrapped_tool.run({"expression": "6 * 7"})
        self.assertIn("Result: 42", result)


if __name__ == '__main__':
    unittest.main(verbosity=2)