import base64
import asyncio
from fastmcp import FastMCP

mcp = FastMCP("Test")

@mcp.tool()
async def ingest_handwritten_note(image_bytes: bytes) -> dict:
    print("TYPE:", type(image_bytes))
    print("LENGTH:", len(image_bytes))
    print("START:", image_bytes[:20])
    return {"success": True}

async def main():
    with open("/home/adman-voids/.gemini/antigravity/brain/3a373fd7-9f46-4de4-b461-27d42a9d0a6e/handwritten_note_1779552079844.png", "rb") as f:
        original_bytes = f.read()
    print("ORIGINAL LENGTH:", len(original_bytes))
    
    img_b64 = base64.b64encode(original_bytes).decode("utf-8")
    
    # Simulate MCP call manually
    await ingest_handwritten_note(img_b64)

asyncio.run(main())
