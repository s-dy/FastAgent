import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.protocols.mcp.client import MCPClient


async def main():
    # 使用相对路径或者绝对路径指向修复后的服务器脚本
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')

    print(f"🔧 Using server path: {server_path}")
    print(f"📁 Current working directory: {os.getcwd()}")

    try:
        async with MCPClient(server_source=server_path) as client:
            print("✅ Connected to MCP server")

            # 测试列出工具
            tools = await client.list_tools()
            print("📋 Available tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")

            # 测试调用工具
            print("\n🧮 Testing calculator tool:")
            calc_result = await client.call_tool("calculator", {"expression": "2 + 2"})
            print(f"   Result: {calc_result}")

            print("\n👋 Testing greet tool:")
            greet_result = await client.call_tool("greet", {"name": "Tester"})
            print(f"   Result: {greet_result}")

            # 测试ping
            ping_result = await client.ping()
            print(f"\n📡 Ping result: {ping_result}")

            # 获取传输信息
            transport_info = client.get_transport_info()
            print(f"🔗 Transport info: {transport_info}")

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())