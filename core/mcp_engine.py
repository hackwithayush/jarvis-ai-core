import asyncio
import logging
from typing import Dict, List, Any, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("mcp library not found. MCP Client Engine disabled.")

logger = logging.getLogger(__name__)

class MCPEngine:
    """
    Universal MCP Client Engine.
    Manages connections to external standard MCP servers (e.g., GitHub, Postgres, Slack).
    """
    def __init__(self):
        self._sessions: Dict[str, ClientSession] = {}
        self._contexts: Dict[str, Any] = {} # Holds the stdio_client context managers
        self._lock = asyncio.Lock()

    async def connect_server(self, provider_id: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """Spawns an MCP server via stdio and establishes a session."""
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP library is not installed.")

        async with self._lock:
            if provider_id in self._sessions:
                return # Already connected

            logger.info(f"Connecting to MCP Server: {provider_id} with command: {command} {' '.join(args)}")
            
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )

            # Keep context manager alive
            ctx = stdio_client(server_params)
            read_stream, write_stream = await ctx.__aenter__()
            self._contexts[provider_id] = ctx

            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()
            
            self._sessions[provider_id] = session
            logger.info(f"Successfully initialized MCP Server: {provider_id}")

    async def disconnect_server(self, provider_id: str):
        """Disconnects and cleans up a specific MCP server."""
        async with self._lock:
            if provider_id in self._sessions:
                try:
                    await self._sessions[provider_id].__aexit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error closing session for {provider_id}: {e}")
                del self._sessions[provider_id]
                
            if provider_id in self._contexts:
                try:
                    await self._contexts[provider_id].__aexit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error closing context for {provider_id}: {e}")
                del self._contexts[provider_id]
                
            logger.info(f"Disconnected MCP Server: {provider_id}")

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Aggregates all tools from all connected MCP servers."""
        tools = []
        for provider_id, session in self._sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    # Convert to standard format LLMs expect (JSON Schema)
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": f"{provider_id}__{tool.name}", # Prefix to avoid collisions
                            "description": tool.description or f"Tool from {provider_id}",
                            "parameters": tool.inputSchema
                        }
                    })
            except Exception as e:
                logger.error(f"Failed to get tools from {provider_id}: {e}")
        return tools
        
    async def get_raw_tools(self) -> List[Dict[str, Any]]:
        """Returns tools formatted for the UI display."""
        tools = []
        for provider_id, session in self._sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "provider": provider_id
                    })
            except Exception as e:
                pass
        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Routes a tool call to the appropriate MCP server and executes it."""
        if "__" not in tool_name:
            return f"Error: Invalid tool format '{tool_name}'."
            
        provider_id, actual_tool_name = tool_name.split("__", 1)
        
        if provider_id not in self._sessions:
            return f"Error: MCP Server '{provider_id}' is not connected."
            
        try:
            logger.info(f"Calling MCP Tool '{actual_tool_name}' on '{provider_id}'...")
            result = await self._sessions[provider_id].call_tool(actual_tool_name, arguments)
            
            # MCP returns a CallToolResult containing content chunks
            output = ""
            for content in result.content:
                if content.type == "text":
                    output += content.text
                elif content.type == "image":
                    output += "[Image content returned]"
                else:
                    output += str(content)
                    
            if result.isError:
                return f"Error from tool: {output}"
                
            return output
        except Exception as e:
            logger.error(f"Execution failed for tool {tool_name}: {e}")
            return f"Error executing tool: {e}"

# Global singleton instance
mcp_engine = MCPEngine()
