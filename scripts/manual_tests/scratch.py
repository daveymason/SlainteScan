import asyncio
from fastmcp import FastMCP
import mcp.types as mt

mcp = FastMCP("test")

@mcp.tool()
async def ingest_handwritten_note(image_bytes: bytes) -> dict:
    pass

async def test():
    # Try to generate the tools list
    tools = await mcp._mcp_server.list_tools()
    print(tools)

asyncio.run(test())
