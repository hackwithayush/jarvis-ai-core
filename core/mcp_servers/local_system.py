#!/usr/bin/env python3
import os
import sys
import json
import subprocess

def run_command(command: str) -> dict:
    """Executes a shell command and returns the output."""
    try:
        # Run in a secure sandbox/subprocess
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30 seconds.", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

def read_file(path: str) -> dict:
    """Reads a file from the local filesystem."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {"content": f.read(), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

def write_file(path: str, content: str) -> dict:
    """Writes to a file on the local filesystem."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"message": f"Successfully wrote to {path}", "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

def list_tools():
    """Return the list of available tools."""
    return [
        {
            "name": "run_terminal_command",
            "description": "Execute a shell command on the host OS. Use carefully.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command line string to execute in Powershell/CMD."
                    }
                },
                "required": ["command"]
            }
        },
        {
            "name": "read_file",
            "description": "Read the contents of a local file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file."
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Write contents to a local file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    ]

def main():
    # Very simple MCP-like stdout/stdin server
    # We read JSON lines from stdin, and output JSON lines to stdout
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            req = json.loads(line.strip())
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "local_system", "version": "1.0.0"}
                    }
                }
                print(json.dumps(response), flush=True)
            elif method == "notifications/initialized" or method == "initialized":
                # Just acknowledge or do nothing, it's a notification
                pass
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": list_tools()}
                }
                print(json.dumps(response), flush=True)
                
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                
                result = {"success": False, "error": "Unknown tool"}
                
                if name == "run_terminal_command":
                    result = run_command(args.get("command", ""))
                elif name == "read_file":
                    result = read_file(args.get("path", ""))
                elif name == "write_file":
                    result = write_file(args.get("path", ""), args.get("content", ""))
                    
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result)}
                        ],
                        "isError": not result.get("success", False)
                    }
                }
                print(json.dumps(response), flush=True)
                
        except Exception as e:
            # Output error over stderr so it doesn't break JSON-RPC
            print(f"Server error: {e}", file=sys.stderr, flush=True)

if __name__ == "__main__":
    main()
