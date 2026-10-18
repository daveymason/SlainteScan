import asyncio
from src.mcp_server import mcp

async def test():
    tools = await mcp._mcp_server.list_tools()
    print("Tools listed successfully!")
    print(tools)

asyncio.run(test())
