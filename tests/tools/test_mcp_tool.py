import unittest
import asyncio
from unittest.mock import AsyncMock, patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastagent.tools.builtin.mcp_tool import MCPTool
from fastagent.tools.builtin.mcp_wrapper_tool import MCPWrappedTool


class TestMCPToolInitialization(unittest.TestCase):
    """MCP工具初始化测试"""

    @patch('src.protocols.mcp.client.MCPClient')
    def test_basic_initialization(self, mock_mcp_client):
        """测试基本初始化"""
        # Mock客户端
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[])
        mock_mcp_client.return_value = mock_client_instance

        # 测试初始化
        tool = MCPTool(
            name="test_mcp",
            server_command=["python", "/Users/sdy/TravelAgent/tests/protocols/mcp/server.py"],
            server_args=["--port", "8080"]
        )

        self.assertEqual(tool.name, "test_mcp")
        self.assertEqual(tool.server_command, ["python", "/Users/sdy/TravelAgent/tests/protocols/mcp/server.py"])
        self.assertEqual(tool.server_args, ["--port", "8080"])
        self.assertTrue(tool.auto_expand)

    @patch('src.protocols.mcp.client.MCPClient')
    def test_initialization_with_env(self, mock_mcp_client):
        """测试带环境变量的初始化"""
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[])
        mock_mcp_client.return_value = mock_client_instance

        env_vars = {"API_KEY": "test_key", "DEBUG": "true"}
        tool = MCPTool(
            name="test_mcp",
            server_command="http://localhost:8080/mcp",
            env=env_vars
        )

        self.assertEqual(tool.env, env_vars)

    @patch('src.protocols.mcp.client.MCPClient')
    def test_auto_expand_behavior(self, mock_mcp_client):
        """测试自动展开行为"""
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[
            {"name": "calculator", "description": "计算工具"},
            {"name": "greet", "description": "问候工具"}
        ])
        mock_mcp_client.return_value = mock_client_instance

        # 测试自动展开模式
        tool_auto = MCPTool(name="test_mcp", auto_expand=True,server_command="http://localhost:8080/mcp")
        self.assertTrue(tool_auto.auto_expand)
        self.assertEqual(tool_auto.prefix, "test_mcp_")

        # 测试非展开模式
        tool_no_auto = MCPTool(name="test_mcp", auto_expand=False,server_command="http://localhost:8080/mcp")
        self.assertFalse(tool_no_auto.auto_expand)
        self.assertEqual(tool_no_auto.prefix, "")

    @patch('utils.async_event.run_async_event')
    @patch('src.protocols.mcp.client.MCPClient')
    def test_tool_discovery(self, mock_mcp_client, mock_run_async):
        """测试工具发现功能"""
        # Mock异步事件运行器
        mock_tools_data = [
            {"name": "tool1", "description": "工具1"},
            {"name": "tool2", "description": "工具2"}
        ]
        mock_run_async.return_value = mock_tools_data

        tool = MCPTool(name="test_mcp", server_command="http://localhost:8080/mcp")
        print(tool.get_expanded_tools())
        # 验证工具发现被调用
        self.assertEqual(len(tool._available_tools), 2)


class TestMCPToolDescriptionGeneration(unittest.TestCase):
    """MCP工具描述生成测试"""

    @patch('src.protocols.mcp.client.MCPClient')
    def test_generate_description_no_tools(self, mock_mcp_client):
        """测试无工具时的描述生成"""
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[])
        mock_mcp_client.return_value = mock_client_instance

        tool = MCPTool(name="test_mcp", server_command="http://localhost:8000/mcp")
        description = tool._generate_description()
        
        self.assertIn("MCP 服务器", description)
        self.assertIn("工具", description)

    @patch('src.protocols.mcp.client.MCPClient')
    def test_generate_description_auto_expand(self, mock_mcp_client):
        """测试展开模式的描述生成"""
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[
            {"name": "calculator", "description": "计算工具"},
            {"name": "greet", "description": "问候工具"}
        ])
        mock_mcp_client.return_value = mock_client_instance

        tool = MCPTool(name="test_mcp", auto_expand=True,server_command="http://localhost:8080/mcp")
        description = tool._generate_description()
        print(description)
        self.assertIn("2个工具", description)
        self.assertIn("自动展开", description)

    @patch('src.protocols.mcp.client.MCPClient')
    def test_generate_description_detailed(self, mock_mcp_client):
        """测试详细描述生成"""
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[
            {"name": "calculator", "description": "计算数学表达式"},
            {"name": "greet", "description": "生成问候语"}
        ])
        mock_mcp_client.return_value = mock_client_instance

        tool = MCPTool(name="test_mcp", auto_expand=False,server_command="http://localhost:8080/mcp")
        description = tool._generate_description()
        
        self.assertIn("bing_search", description)
        self.assertIn("crawl_webpage", description)
        self.assertIn("调用格式", description)


class TestMCPToolRunMethod(unittest.TestCase):
    """MCP工具run方法测试"""

    @patch('utils.async_event.run_async_event')
    @patch('src.protocols.mcp.client.MCPClient')
    def test_run_list_tools(self, mock_mcp_client, mock_run_async):
        """测试列出工具功能"""
        mock_tools_result = [
            {"name": "calculator", "description": "计算工具"},
            {"name": "greet", "description": "问候工具"}
        ]

        async def mock_operation():
            return "找到 2 个工具:\n- calculator: 计算工具\n- greet: 问候工具\n"
        
        mock_run_async.return_value = asyncio.run(mock_operation())

        tool = MCPTool(name="test_mcp", server_command="http://localhost:8080/mcp")
        result = tool.run({"action": "list_tools"})
        
        self.assertIn("找到 2 个工具", result)
        self.assertIn("bing_search", result)

    @patch('utils.async_event.run_async_event')
    @patch('src.protocols.mcp.client.MCPClient')
    def test_run_call_tool(self, mock_mcp_client, mock_run_async):
        """测试调用工具功能"""
        async def mock_operation():
            return "工具 'calculator' 执行结果:\nResult: 4"
        
        mock_run_async.return_value = asyncio.run(mock_operation())

        tool = MCPTool(name="test_mcp", server_command="http://localhost:8080/mcp")
        result = tool.run({
            "action": "call_tool",
            "tool_name": "bing_search",
            "arguments": {"query": "python"}
        })
        
        self.assertIn("bing_search", result)
        self.assertIn("python", result)

    @patch('utils.async_event.run_async_event')
    @patch('src.protocols.mcp.client.MCPClient')
    def test_run_smart_action_inference(self, mock_mcp_client, mock_run_async):
        """测试智能动作推断"""
        async def mock_operation():
            return "工具 'greet' 执行结果:\nHello, World!"
        
        mock_run_async.return_value = asyncio.run(mock_operation())

        tool = MCPTool(name="test_mcp", server_command="http://localhost:8080/mcp")
        # 不指定action，但指定tool_name，应该自动推断为call_tool
        result = tool.run({
            "tool_name": "search",
            "arguments": {"query": "python"}
        })
        
        self.assertIn("search", result)

    @patch('utils.async_event.run_async_event')
    @patch('src.protocols.mcp.client.MCPClient')
    def test_run_error_handling(self, mock_mcp_client, mock_run_async):
        """测试错误处理"""
        mock_run_async.side_effect = Exception("连接失败")

        tool = MCPTool(name="test_mcp", server_command="http://localhost:8000/mcp")
        result = tool.run({"action": "list_tools"})
        
        self.assertIn("MCP 操作失败", result)

    @patch('utils.async_event.run_async_event')
    @patch('src.protocols.mcp.client.MCPClient')
    def test_run_invalid_action(self, mock_mcp_client, mock_run_async):
        """测试无效动作处理"""
        tool = MCPTool(name="test_mcp", server_command="http://localhost:8080/mcp")
        result = tool.run({"action": "invalid_action"})
        
        self.assertIn("不支持的操作", result)
        self.assertIn("invalid_action", result)


class TestMCPToolGetParameters(unittest.TestCase):
    """MCP工具参数获取测试"""

    @patch('src.protocols.mcp.client.MCPClient')
    def test_get_parameters(self, mock_mcp_client):
        """测试获取参数定义"""
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[])
        mock_mcp_client.return_value = mock_client_instance

        tool = MCPTool(name="test_mcp", server_command="http://localhost:8080/mcp")
        parameters = tool.get_parameters()
        
        # 验证必需参数存在
        param_names = [param.name for param in parameters]
        self.assertIn("action", param_names)
        self.assertIn("tool_name", param_names)
        self.assertIn("arguments", param_names)
        
        # 验证参数类型
        action_param = next(p for p in parameters if p.name == "action")
        self.assertEqual(action_param.type, "string")
        self.assertTrue(action_param.required)


class TestMCPToolExpandedTools(unittest.TestCase):
    """MCP工具展开测试"""

    @patch('src.protocols.mcp.client.MCPClient')
    def test_get_expanded_tools_auto_expand(self, mock_mcp_client):
        """测试获取展开工具（自动展开模式）"""
        tool = MCPTool(name="filesystem", auto_expand=True, server_command="http://localhost:8080/mcp")
        expanded_tools = tool.get_expanded_tools()
        
        self.assertEqual(len(expanded_tools), 2)
        self.assertIsInstance(expanded_tools[0], MCPWrappedTool)
        
        # 验证工具名称前缀
        tool_names = [t.name for t in expanded_tools]
        self.assertIn("filesystem_bing_search", tool_names)
        self.assertIn("filesystem_crawl_webpage", tool_names)

    @patch('src.protocols.mcp.client.MCPClient')
    def test_get_expanded_tools_no_auto_expand(self, mock_mcp_client):
        """测试获取展开工具（非展开模式）"""
        mock_client_instance = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[
            {"name": "calculator", "description": "计算工具"}
        ])
        mock_mcp_client.return_value = mock_client_instance

        tool = MCPTool(name="test_mcp", auto_expand=False, server_command="http://localhost:8080/mcp")
        expanded_tools = tool.get_expanded_tools()
        
        self.assertEqual(len(expanded_tools), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)