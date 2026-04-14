import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    server_params = StdioServerParameters(
        command="python3",
        args=["agents/mcp_server.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Connected to MCP server. Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # Call plan_event tool
            print("\nCalling plan_event tool...")
            result = await session.call_tool(
                "plan_event",
                arguments={
                    "event_type": "wedding",
                    "location": "Lahore",
                    "budget": 10000,
                    "attendees": 200,
                    "date": "2025-03-15",
                    "preferences": ["outdoor"]
                }
            )
            print(f"Result: {result.content}")

if __name__ == "__main__":
    asyncio.run(run())
