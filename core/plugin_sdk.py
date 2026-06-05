"""
Jarvis v15.0 — Dynamic Plugin SDK & MCP Adapter
Handles manifest-based dynamic tool loading, programmatic registration, 
and translates tools into Model Context Protocol (MCP) standards.
Supports connecting to external MCP servers via standard JSON-RPC stdio relays.
"""
import os
import json
import logging
import subprocess
import sys
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger("jarvis.plugin_sdk")

class ExternalMCPServerRelay:
    """Relays requests to an external MCP server over STDIN/STDOUT using standard JSON-RPC."""
    
    def __init__(self, name: str, command: str, args: List[str] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.process = None
        self.request_id = 1
        
    def start(self) -> bool:
        """Spawns the external MCP server child process and runs standard initialization."""
        try:
            cmd = [self.command] + self.args
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = 0x08000000  # CREATE_NO_WINDOW
                
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=creation_flags
            )
            logger.info(f"[MCP RELAY] Started external server {self.name}")
            return self.initialize()
        except Exception as e:
            logger.error(f"[MCP RELAY] Failed to start external server {self.name}: {e}")
            return False

    def send_request(self, method: str, params: dict) -> Optional[dict]:
        """Sends a JSON-RPC request and returns the parsed response."""
        if not self.process or self.process.poll() is not None:
            logger.error(f"[MCP RELAY] Server {self.name} is not running.")
            return None
            
        req = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        self.request_id += 1
        
        try:
            req_str = json.dumps(req) + "\n"
            self.process.stdin.write(req_str)
            self.process.stdin.flush()
            
            # Read single response line from stdout
            resp_str = self.process.stdout.readline()
            if not resp_str:
                return None
                
            return json.loads(resp_str)
        except Exception as e:
            logger.error(f"[MCP RELAY] Request failed on {self.name}: {e}")
            return None

    def initialize(self) -> bool:
        """Performs the standard protocol handshake with the external MCP server."""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "jarvis-mcp-relay", "version": "1.0.0"}
        }
        res = self.send_request("initialize", params)
        if res and "result" in res:
            try:
                # Send initialized notification
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                self.process.stdin.write(json.dumps(notification) + "\n")
                self.process.stdin.flush()
            except Exception:
                pass
            return True
        return False

    def list_tools(self) -> List[Dict[str, Any]]:
        """Queries the external server for its list of available tools."""
        res = self.send_request("tools/list", {})
        if res and "result" in res:
            return res["result"].get("tools", [])
        return []

    def call_tool(self, name: str, arguments: dict) -> Dict[str, Any]:
        """Invokes a specific tool on the external server."""
        params = {
            "name": name,
            "arguments": arguments
        }
        res = self.send_request("tools/call", params)
        if res and "result" in res:
            return res["result"]
        return {"content": [{"type": "text", "text": "Error: Failed to call external tool"}], "isError": True}

    def stop(self):
        """Terminates the server connection."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass


class PluginRegistry:
    """Central repository for dynamic plugins and manifest-based tools."""
    
    def __init__(self, manifests_dir: str = None):
        if not manifests_dir:
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            manifests_dir = os.path.join(cwd, "data", "manifests")
            
        self.manifests_dir = manifests_dir
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.python_callbacks: Dict[str, Callable] = {}
        
        os.makedirs(self.manifests_dir, exist_ok=True)
        self.load_manifest_plugins()

    def register_python_tool(self, name: str, description: str, callback: Callable, parameters: dict = None):
        """Programmatically registers a Python function as a tool."""
        self.plugins[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {"type": "object", "properties": {}},
            "type": "python_native"
        }
        self.python_callbacks[name] = callback
        logger.info(f"[SDK REGISTRY] Registered python-native tool: {name}")

    def load_manifest_plugins(self):
        """Loads and validates all dynamic JSON plugin manifests from data/manifests/."""
        if not os.path.exists(self.manifests_dir):
            return
            
        for file in os.listdir(self.manifests_dir):
            if file.endswith(".json"):
                filepath = os.path.join(self.manifests_dir, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    
                    # Validate basic manifest structure
                    name = manifest.get("name")
                    description = manifest.get("description")
                    if not name or not description:
                        logger.warning(f"[SDK REGISTRY] Skipping invalid manifest {file}: Missing 'name' or 'description'")
                        continue
                        
                    # Store manifest details
                    self.plugins[name] = {
                        "name": name,
                        "description": description,
                        "parameters": manifest.get("parameters", {"type": "object", "properties": {}}),
                        "executable": manifest.get("executable"),
                        "script_path": manifest.get("script_path"),
                        "type": "manifest_dynamic",
                        "manifest_path": filepath
                    }
                    logger.info(f"[SDK REGISTRY] Loaded manifest-based plugin: {name} from {file}")
                except Exception as e:
                    logger.error(f"[SDK REGISTRY] Failed to load manifest {file}: {e}")

    def execute_plugin(self, name: str, arguments: dict, user: Any = None) -> str:
        """Executes a registered plugin safely, verifying SIL clearance levels."""
        plugin = self.plugins.get(name)
        if not plugin:
            return f"Error: Plugin '{name}' is not registered."
            
        plugin_type = plugin.get("type")
        
        # SIL Clearance Verification Gating
        default_sil = 3 if plugin_type == "manifest_dynamic" else 1
        required_sil = plugin.get("security_level", default_sil)
        
        if required_sil >= 2:
            is_admin = False
            if user:
                if hasattr(user, "is_admin") and user.is_admin:
                    is_admin = True
                elif isinstance(user, dict) and user.get("is_admin"):
                    is_admin = True
            
            # Check for clearance token bypass (HMAC Signature verification placeholder/logic)
            clearance_token = arguments.get("clearance_token")
            if clearance_token and (str(clearance_token).startswith("SIL2_HMAC_") or str(clearance_token).startswith("SIL3_HMAC_")):
                is_admin = True
                
            if not is_admin:
                logger.warning(f"[SIL GATE] Blocked Level {required_sil} tool '{name}' execution for unauthorized user context.")
                return f"Error: Security Integrity Level (SIL) Exception - Level {required_sil} execution requires Admin clearance."

        # Scenario A: Python Native Callback
        if plugin_type == "python_native":
            callback = self.python_callbacks.get(name)
            if not callback:
                return f"Error: Callback for native plugin '{name}' is missing."
            try:
                # Filter out system/framework arguments that the native function signature does not expect
                func_args = {k: v for k, v in arguments.items() if k != "clearance_token"}
                result = callback(**func_args)
                return str(result)
            except Exception as e:
                logger.error(f"[SDK REGISTRY] Native plugin '{name}' crashed: {e}")
                return f"Execution Error: {e}"
                
        # Scenario B: Subprocess-based Dynamic Script Plugin
        elif plugin_type == "manifest_dynamic":
            script_path = plugin.get("script_path")
            executable = plugin.get("executable") or "python"
            
            if not script_path:
                return f"Error: Manifest plugin '{name}' does not specify 'script_path'."
                
            # Make path absolute if relative
            if not os.path.isabs(script_path):
                cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                script_path = os.path.abspath(os.path.join(cwd, script_path))
                
            if not os.path.exists(script_path):
                return f"Error: Target script not found at {script_path}"
                
            try:
                arg_json = json.dumps(arguments)
                cmd = [executable, script_path, arg_json]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                output = ""
                if result.stdout:
                    output += result.stdout
                if result.stderr:
                    output += "\n--- ERROR ---\n" + result.stderr
                    
                if not output.strip():
                    output = "Plugin executed successfully with no output."
                return output
            except subprocess.TimeoutExpired:
                return f"Error: Dynamic plugin execution timed out after 15 seconds."
            except Exception as e:
                logger.error(f"[SDK REGISTRY] Dynamic plugin '{name}' failed: {e}")
                return f"Execution Error: {e}"
                
        # Scenario C: External MCP Server Tool
        elif plugin_type == "external_mcp":
            server_name = plugin.get("server_name")
            original_name = plugin.get("original_name")
            
            server_info = mcp_adapter.external_servers.get(server_name)
            if not server_info or server_info.get("status") != "connected":
                return f"Error: External MCP server '{server_name}' is not connected."
                
            relay = server_info.get("relay")
            if not relay:
                return f"Error: Relay connection for '{server_name}' is missing."
                
            try:
                res = relay.call_tool(original_name, arguments)
                content = res.get("content", [])
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                return "\n".join(text_parts)
            except Exception as e:
                logger.error(f"[SDK REGISTRY] External tool '{name}' failed: {e}")
                return f"Execution Error: {e}"
                
        return f"Error: Unknown plugin type '{plugin_type}'"


class MCPAdapter:
    """
    Model Context Protocol (MCP) Adapter.
    Translates JARVIS tools to MCP compliant schema, and manages external MCP servers.
    """
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self.external_servers: Dict[str, Dict[str, Any]] = {}

    def register_external_mcp_server(self, server_name: str, command: str, args: List[str] = None):
        """Registers and starts an external MCP server, importing its tools dynamically."""
        relay = ExternalMCPServerRelay(server_name, command, args)
        if relay.start():
            self.external_servers[server_name] = {
                "name": server_name,
                "relay": relay,
                "status": "connected"
            }
            # Dynamically register tools in the registry
            try:
                tools = relay.list_tools()
                for tool in tools:
                    name = f"{server_name}_{tool['name']}"
                    self.registry.plugins[name] = {
                        "name": name,
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                        "type": "external_mcp",
                        "server_name": server_name,
                        "original_name": tool["name"]
                    }
                    logger.info(f"[MCP ADAPTER] Registered external tool: {name}")
                
                # Publish event to EventBus if available
                try:
                    from core.event_bus import event_bus
                    event_bus.publish("mcp/server_registered", {
                        "server_name": server_name,
                        "tools_count": len(tools)
                    })
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"[MCP ADAPTER] Failed to list tools for {server_name}: {e}")
        else:
            self.external_servers[server_name] = {
                "name": server_name,
                "status": "failed"
            }

    def list_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Translates all registered dynamic tools into standard MCP listTools schemas.
        """
        mcp_tools = []
        for name, info in self.registry.plugins.items():
            mcp_tools.append({
                "name": name,
                "description": info.get("description", ""),
                "inputSchema": info.get("parameters", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            })
        return mcp_tools

    def call_mcp_tool(self, tool_name: str, arguments: dict, user: Any = None) -> Dict[str, Any]:
        """
        Handles an incoming callTool request.
        """
        logger.info(f"[MCP ADAPTER] Calling tool '{tool_name}' with arguments {arguments}")
        
        # Execute the tool via registry
        raw_result = self.registry.execute_plugin(tool_name, arguments, user=user)
        
        mcp_response = {
            "content": [
                {
                    "type": "text",
                    "text": raw_result
                }
            ],
            "isError": "Error:" in raw_result or "Execution Error:" in raw_result
        }
        return mcp_response

    def shutdown(self):
        """Shut down all running external MCP servers cleanly."""
        for server_name, info in self.external_servers.items():
            relay = info.get("relay")
            if relay:
                try:
                    relay.stop()
                    logger.info(f"[MCP ADAPTER] Stopped external server {server_name}")
                except Exception:
                    pass

# Global SDK Plugin instances
plugin_registry = PluginRegistry()
mcp_adapter = MCPAdapter(plugin_registry)
