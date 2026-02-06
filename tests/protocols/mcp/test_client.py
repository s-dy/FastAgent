import unittest
import asyncio
import tempfile
from unittest.mock import AsyncMock, Mock, patch
from fastagent.protocols.mcp.client import MCPClient


class TestMCPClient(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        self.loop.close()
        # 清理临时目录
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_init_with_python_script(self, mock_transport):
        """测试使用Python脚本初始化客户端"""
        mock_instance = Mock()
        mock_transport.return_value = mock_instance

        client = MCPClient(server_source="/path/to/server.py")

        mock_transport.assert_called_once_with(
            script_path="/path/to/server.py",
            args=[],
            env=None
        )
        self.assertEqual(client.server_source, mock_instance)

    @patch('src.protocols.mcp.client.StreamableHttpTransport')
    def test_init_with_http_url(self, mock_transport):
        """测试使用HTTP URL初始化客户端"""
        mock_instance = Mock()
        mock_transport.return_value = mock_instance

        client = MCPClient(server_source="http://localhost:8080/mcp")

        mock_transport.assert_called_once_with(url="http://localhost:8080/mcp")
        self.assertEqual(client.server_source, mock_instance)

    @patch('src.protocols.mcp.client.SSETransport')
    def test_init_with_sse_url(self, mock_transport):
        """测试使用SSE URL初始化客户端"""
        mock_instance = Mock()
        mock_transport.return_value = mock_instance

        client = MCPClient(
            server_source="http://localhost:8080/mcp",
            transport_type="sse"
        )

        mock_transport.assert_called_once_with(url="http://localhost:8080/mcp")
        self.assertEqual(client.server_source, mock_instance)

    @patch('src.protocols.mcp.client.StdioTransport')
    def test_init_with_command_list(self, mock_transport):
        """测试使用命令列表初始化客户端"""
        mock_instance = Mock()
        mock_transport.return_value = mock_instance

        client = MCPClient(server_source=["python", "server.py", "--port", "8080"])

        mock_transport.assert_called_once_with(
            command="python",
            args=["server.py", "--port", "8080"],
            env=None
        )
        self.assertEqual(client.server_source, mock_instance)

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_context_manager_enter(self, mock_transport, mock_client_class):
        """测试上下文管理器进入"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # Mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                # 验证客户端被正确创建和连接
                mock_client_class.assert_called_once_with(mock_transport_instance)
                mock_client.__aenter__.assert_called_once()
                self.assertIsNotNone(client.client)

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_context_manager_exit(self, mock_transport, mock_client_class):
        """测试上下文管理器退出"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # Mock client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                pass  # 上下文管理器会自动退出

            # 验证连接被正确关闭
            mock_client.__aexit__.assert_called_once()

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_ping_success(self, mock_transport, mock_client_class):
        """测试ping成功"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # Mock client
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                result = await client.ping()
                self.assertTrue(result)
                mock_client.ping.assert_called_once()

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_ping_failure(self, mock_transport, mock_client_class):
        """测试ping失败"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # Mock client
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                result = await client.ping()
                self.assertFalse(result)

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_list_tools(self, mock_transport, mock_client_class):
        """测试列出工具"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # 创建模拟的工具对象
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool1.description = "Tool 1 description"
        mock_tool1.inputSchema = {"type": "object"}
        mock_tool1.outputSchema = {"type": "string"}

        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        mock_tool2.description = "Tool 2 description"
        mock_tool2.inputSchema = {"type": "array"}
        mock_tool2.outputSchema = {"type": "number"}

        mock_result = Mock()
        mock_result.tools = [mock_tool1, mock_tool2]

        # Mock client
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                tools = await client.list_tools()

                self.assertEqual(len(tools), 2)
                self.assertEqual(tools[0]["name"], "tool1")
                self.assertEqual(tools[0]["description"], "Tool 1 description")
                self.assertEqual(tools[0]["input_schema"], {"type": "object"})
                self.assertEqual(tools[1]["name"], "tool2")
                self.assertEqual(tools[1]["description"], "Tool 2 description")

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_call_tool(self, mock_transport, mock_client_class):
        """测试调用工具"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # 创建模拟的结果对象
        mock_content = Mock()
        mock_content.text = "Tool execution result"

        mock_result = Mock()
        mock_result.content = [mock_content]

        # Mock client
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                result = await client.call_tool("test_tool", {"param": "value"})
                self.assertEqual(result, "Tool execution result")
                mock_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_list_resources(self, mock_transport, mock_client_class):
        """测试列出资源"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # 创建模拟的资源对象
        mock_resource1 = Mock()
        mock_resource1.uri = "file:///test/resource1.txt"
        mock_resource1.name = "Resource 1"
        mock_resource1.description = "Test resource 1"
        mock_resource1.mimeType = "text/plain"

        mock_resource2 = Mock()
        mock_resource2.uri = "file:///test/resource2.json"
        mock_resource2.name = "Resource 2"
        mock_resource2.description = "Test resource 2"
        mock_resource2.mimeType = "application/json"

        mock_result = Mock()
        mock_result.resources = [mock_resource1, mock_resource2]

        # Mock client
        mock_client = AsyncMock()
        mock_client.list_resources = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                resources = await client.list_resources()

                self.assertEqual(len(resources), 2)
                self.assertEqual(resources[0]["uri"], "file:///test/resource1.txt")
                self.assertEqual(resources[0]["name"], "Resource 1")
                self.assertEqual(resources[0]["mime_type"], "text/plain")
                self.assertEqual(resources[1]["uri"], "file:///test/resource2.json")

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_read_resource(self, mock_transport, mock_client_class):
        """测试读取资源"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # 创建模拟的内容对象
        mock_content = Mock()
        mock_content.text = "Resource content"

        mock_result = Mock()
        mock_result.contents = [mock_content]

        # Mock client
        mock_client = AsyncMock()
        mock_client.read_resource = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                result = await client.read_resource("file:///test/resource.txt")
                self.assertEqual(result, "Resource content")
                mock_client.read_resource.assert_called_once_with("file:///test/resource.txt")

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_list_prompts(self, mock_transport, mock_client_class):
        """测试列出提示词模板"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # 创建模拟的提示词对象
        mock_prompt1 = Mock()
        mock_prompt1.name = "prompt1"
        mock_prompt1.description = "Prompt 1 description"
        mock_prompt1.arguments = [{"name": "arg1", "required": True}]

        mock_prompt2 = Mock()
        mock_prompt2.name = "prompt2"
        mock_prompt2.description = "Prompt 2 description"
        mock_prompt2.arguments = []

        mock_result = Mock()
        mock_result.prompts = [mock_prompt1, mock_prompt2]

        # Mock client
        mock_client = AsyncMock()
        mock_client.list_prompts = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                prompts = await client.list_prompts()

                self.assertEqual(len(prompts), 2)
                self.assertEqual(prompts[0]["name"], "prompt1")
                self.assertEqual(prompts[0]["description"], "Prompt 1 description")
                self.assertEqual(prompts[1]["name"], "prompt2")

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_get_prompt(self, mock_transport, mock_client_class):
        """测试获取提示词内容"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        # 创建模拟的消息对象
        mock_content = Mock()
        mock_content.text = "Hello, {{name}}!"

        mock_message = Mock()
        mock_message.role = "user"
        mock_message.content = mock_content

        mock_result = Mock()
        mock_result.messages = [mock_message]

        # Mock client
        mock_client = AsyncMock()
        mock_client.get_prompt = AsyncMock(return_value=mock_result)
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                messages = await client.get_prompt("greeting_prompt", {"name": "World"})

                self.assertEqual(len(messages), 1)
                self.assertEqual(messages[0]["role"], "user")
                self.assertEqual(messages[0]["content"], "Hello, {{name}}!")
                mock_client.get_prompt.assert_called_once_with("greeting_prompt", {"name": "World"})

        self.loop.run_until_complete(test_async())

    @patch('src.protocols.mcp.client.Client')
    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_get_transport_info_connected(self, mock_transport, mock_client_class):
        """测试获取传输信息（已连接）"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        mock_transport_instance.__class__.__name__ = "PythonStdioTransport"
        mock_transport_instance.__str__ = Mock(return_value="transport_details")

        # Mock client
        mock_client = AsyncMock()
        mock_client.transport = mock_transport_instance
        mock_client_class.return_value = mock_client

        async def test_async():
            async with MCPClient(server_source="/test/script.py") as client:
                info = client.get_transport_info()

                self.assertEqual(info["status"], "connected")
                self.assertEqual(info["transport_type"], "PythonStdioTransport")
                self.assertEqual(info["transport_info"], "transport_details")

        self.loop.run_until_complete(test_async())

    def test_get_transport_info_not_connected(self):
        """测试获取传输信息（未连接）"""
        client = MCPClient(server_source="/test/script.py")
        # 不使用上下文管理器，client.client 为 None

        info = client.get_transport_info()
        self.assertEqual(info["status"], "not_connected")

    @patch('src.protocols.mcp.client.PythonStdioTransport')
    def test_methods_without_connection(self, mock_transport):
        """测试未连接时调用方法"""
        # Mock transport
        mock_transport_instance = Mock()
        mock_transport.return_value = mock_transport_instance

        client = MCPClient(server_source="/test/script.py")

        async def test_async():
            with self.assertRaises(RuntimeError) as context:
                await client.list_tools()
            self.assertIn("Client not connected", str(context.exception))

            with self.assertRaises(RuntimeError) as context:
                await client.call_tool("test", {})
            self.assertIn("Client not connected", str(context.exception))

            with self.assertRaises(RuntimeError) as context:
                await client.ping()
            self.assertIn("Client not connected", str(context.exception))

        self.loop.run_until_complete(test_async())


if __name__ == '__main__':
    unittest.main()