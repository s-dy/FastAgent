import unittest
import asyncio
import os
import sys

from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from fastagent.protocols.mcp.client import MCPClient
from fastagent.protocols.mcp.server import MCPServer


class TestMCPClientBasic(unittest.TestCase):
    """MCP客户端基础测试"""

    def test_client_initialization_with_http(self):
        """测试HTTP传输的客户端初始化"""
        test_cases = [
            "http://localhost:8000/mcp",
        ]

        for server_source in test_cases:
            client = MCPClient(server_source=server_source)
            self.assertIsNotNone(client)
            # 验证传输类型检测
            self.assertTrue(
                hasattr(client.server_source, '__class__') or
                isinstance(client.server_source, str)
            )

    def test_client_initialization_with_config(self):
        """测试配置字典初始化"""
        config_cases = [
            {"transport": "streamable", "url": "http://localhost:8000/mcp"},
            {"transport": "sse", "url": "http://localhost:8000/events"},
        ]

        for config in config_cases:
            client = MCPClient(server_source=config)
            self.assertIsNotNone(client)

    def test_transport_type_detection(self):
        """测试传输类型自动检测"""
        # HTTP URL检测
        http_client = MCPClient(server_source="http://localhost:8000/mcp")
        self.assertTrue(hasattr(http_client.server_source, '__class__'))

        # HTTPS URL检测
        https_client = MCPClient(server_source="http://localhost:8000/mcp")
        self.assertTrue(hasattr(https_client.server_source, '__class__'))


class TestMCPServerDirect(unittest.TestCase):
    """MCP服务器直接测试"""

    def setUp(self):
        """测试前置准备"""
        self.server = MCPServer(name="UnitTestServer", description="单元测试服务器")

    def test_server_initialization(self):
        """测试服务器初始化"""
        self.assertEqual(self.server.name, "UnitTestServer")
        self.assertEqual(self.server.description, "单元测试服务器")

        info = self.server.get_info()
        self.assertEqual(info["name"], "UnitTestServer")
        self.assertEqual(info["description"], "单元测试服务器")
        self.assertEqual(info["protocol"], "MCP")

    def test_tool_registration_mock(self):
        """测试工具注册（使用mock避免实际执行）"""
        # 创建mock函数
        def add(a, b):
            """add tool"""
            return a + b

        # 注册工具
        self.server.add_tool(add, name="add_numbers", description="加法工具")

        # 验证服务器基本信息仍然正确
        info = self.server.get_info()
        self.assertEqual(info["name"], "UnitTestServer")

    def test_resource_registration_mock(self):
        """测试资源注册"""
        def resource(dummy):
            """resource tool"""
            return "fsdfs{uri}dasd"

        # 注册资源
        self.server.add_resource(
            resource,
            uri="test://resource/{dummy}",
            name="测试资源",
            description="测试用资源"
        )

        # 验证注册没有破坏服务器状态
        info = self.server.get_info()
        self.assertEqual(info["protocol"], "MCP")

    def test_prompt_registration_mock(self):
        """测试提示词注册"""
        def prompt_func(prompt):
            """prompt toolkit"""
            return prompt

        # 注册提示词
        self.server.add_prompt(
            prompt_func,
            name="discussion",
            description="讨论提示词"
        )

        # 验证服务器状态
        info = self.server.get_info()
        self.assertIn("name", info)


class TestMCPClientConfiguration(unittest.TestCase):
    """MCP客户端配置测试"""

    def test_various_server_sources(self):
        """测试各种服务器源配置"""
        test_cases = [
            # HTTP URLs
            "http://localhost:8000/mcp",
            "http://localhost:8000/mcp",
            # Configuration dicts
            {"transport": "sse", "url": "http://localhost:8000/events"},
            {"transport": "streamable", "url": "http://localhost:8000/mcp"},
        ]

        for server_source in test_cases:
            with self.subTest(server_source=server_source):
                client = MCPClient(server_source=server_source)
                self.assertIsNotNone(client)
                print(client.server_source)
                if isinstance(server_source, str):
                    self.assertEqual(client.server_source.url, server_source)
                elif isinstance(server_source, dict):
                    self.assertEqual(client.server_source.url, server_source.get("url"))

    def test_client_with_arguments(self):
        """测试带参数的客户端初始化"""
        client = MCPClient(
            server_source="http://localhost:8000/mcp",
            server_args=["--debug", "--verbose"],
            transport_type="streamable",
            env={"CUSTOM_VAR": "value"}
        )

        self.assertEqual(client.server_args, ["--debug", "--verbose"])
        self.assertEqual(client.transport_type, "streamable")
        self.assertEqual(client.env, {"CUSTOM_VAR": "value"})

    def test_client_with_transport_kwargs(self):
        """测试传输特定参数"""
        client = MCPClient(
            server_source="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer token"}
        )

        self.assertEqual(client.transport_kwargs["headers"]["Authorization"], "Bearer token")


class TestMCPErrorHandling(unittest.TestCase):
    """MCP错误处理测试"""

    def test_client_not_connected_error(self):
        """测试客户端未连接时的错误处理"""
        client = MCPClient(server_source="http://localhost:8000/mcp")

        # 在未连接状态下调用方法应该抛出RuntimeError
        with self.assertRaises(RuntimeError) as context:
            asyncio.run(client.list_tools())

        self.assertIn("Client not connected", str(context.exception))

    def test_invalid_transport_type(self):
        """测试无效传输类型"""
        with self.assertRaises(ValueError):
            MCPClient(
                server_source={"transport": "invalid_type", "url": "http://localhost:8000"}
            )


class TestMCPProtocolValidation(unittest.TestCase):
    """MCP协议验证测试"""

    def test_valid_server_sources(self):
        """测试有效的服务器源格式"""
        valid_sources = [
            "http://localhost:8000/mcp",
            ["python", "server.py"],
            {"transport": "sse", "url": "http://localhost:8000/events"},
        ]

        for source in valid_sources:
            with self.subTest(source=source):
                try:
                    client = MCPClient(server_source=source)
                    self.assertIsNotNone(client)
                except Exception as e:
                    self.fail(f"Valid source {source} failed with: {e}")

    def test_server_info_structure(self):
        """测试服务器信息结构"""
        server = MCPServer(name="TestServer")
        info = server.get_info()

        # 验证必需字段
        required_fields = ["name", "description", "protocol"]
        for field in required_fields:
            self.assertIn(field, info)

        # 验证字段类型
        self.assertIsInstance(info["name"], str)
        self.assertIsInstance(info["description"], str)
        self.assertIsInstance(info["protocol"], str)


# 新增的测试类
class TestMCPServerFunctionality(unittest.TestCase):
    """MCP服务器功能测试"""

    def setUp(self):
        """测试前置准备"""
        self.server = MCPServer(name="FunctionalTestServer", description="功能测试服务器")

    def test_add_tool_function(self):
        """测试添加工具功能"""

        def sample_tool(x: int, y: int) -> int:
            """样本工具函数"""
            return x + y

        # 添加工具
        self.server.add_tool(sample_tool, name="add", description="加法工具")

        # 验证服务器状态
        info = self.server.get_info()
        self.assertEqual(info["name"], "FunctionalTestServer")

    def test_add_resource_function(self):
        """测试添加资源功能"""

        def sample_resource():
            """样本资源函数"""
            return "资源内容"

        # 添加资源
        self.server.add_resource(
            sample_resource,
            uri="file://test/resource.txt",
            name="测试资源",
            description="测试用资源文件"
        )

        # 验证服务器状态
        info = self.server.get_info()
        self.assertEqual(info["protocol"], "MCP")

    def test_add_prompt_function(self):
        """测试添加提示词功能"""

        def sample_prompt(topic: str = "AI") -> List[Dict[str, Any]]:
            """样本提示词函数"""
            return [
                {
                    "role": "user",
                    "content": {"text": f"请讨论{topic}相关话题"}
                }
            ]

        # 添加提示词
        self.server.add_prompt(
            sample_prompt,
            name="discussion_prompt",
            description="讨论提示词模板"
        )

        # 验证服务器状态
        info = self.server.get_info()
        self.assertIn("FunctionalTestServer", info["name"])

    def test_multiple_registrations(self):
        """测试多次注册不同类型的功能"""

        # 添加工具
        def calc_tool(a: float, b: float) -> float:
            return a * b

        self.server.add_tool(calc_tool, name="multiply", description="乘法工具")

        # 添加资源
        def data_resource():
            return {"data": [1, 2, 3, 4, 5]}

        self.server.add_resource(data_resource, uri="data://numbers", name="数字数据")

        # 添加提示词
        def chat_prompt(context: str = "") -> List[Dict[str, Any]]:
            return [
                {
                    "role": "assistant",
                    "content": {"text": f"基于上下文{context}进行对话"}
                }
            ]

        self.server.add_prompt(chat_prompt, name="chat_template")

        # 验证服务器仍然正常工作
        info = self.server.get_info()
        self.assertEqual(info["protocol"], "MCP")
        self.assertEqual(info["name"], "FunctionalTestServer")


class TestMCPClientAdvancedFeatures(unittest.TestCase):
    """MCP客户端高级功能测试"""

    def test_environment_variables_handling(self):
        """测试环境变量处理"""
        env_vars = {
            "API_KEY": "test_key_123",
            "DEBUG": "true",
            "TIMEOUT": "30"
        }

        client = MCPClient(
            server_source="http://localhost:8000/mcp",
            env=env_vars
        )

        self.assertEqual(client.env, env_vars)

    def test_server_args_processing(self):
        """测试服务器参数处理"""
        args = ["--config", "config.yaml", "--port", "8080", "--verbose"]

        client = MCPClient(
            server_source="/Users/sdy/TravelAgent/tests/protocols/mcp/server.py",
            server_args=args
        )

        self.assertEqual(client.server_args, args)

    def test_transport_kwargs_storage(self):
        """测试传输关键字参数存储"""
        transport_kwargs = {
        }

        client = MCPClient(
            server_source="http://localhost:8000/mcp",
            **transport_kwargs
        )

        for key, value in transport_kwargs.items():
            self.assertEqual(client.transport_kwargs[key], value)

    def test_complex_configuration_combinations(self):
        """测试复杂配置组合"""
        client = MCPClient(
            server_source={"transport": "streamable", "url": "http://localhost:8000"},
            server_args=["--debug"],
            transport_type="streamable",
            env={"ENV": "test"},
        )

        # 验证所有配置都被正确存储
        self.assertEqual(client.server_args, ["--debug"])
        self.assertEqual(client.transport_type, "streamable")
        self.assertEqual(client.env, {"ENV": "test"})


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)