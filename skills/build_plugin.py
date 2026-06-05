"""
Jarvis Skill — Build Plugin Manifest (build_plugin)
A skill that dynamically scaffolds and compiles schema-compliant plugin manifests
for newly discovered workstation tools or external MCP adapters, with host network auto-discovery hooks.
"""
import os
import json
import socket

MANIFEST = {
    "skill_id": "build_plugin",
    "name": "Dynamic MCP Plugin Scaffolder",
    "description": "Composite orchestration skill that scaffolds standard-compliant MCP plugin manifests.",
    "required_clearance": "MEDIUM",
    "required_capabilities": [
        "filesystem.write"
    ],
    "parameters": {
        "plugin_id": {
            "type": "string",
            "description": "Unique alphanumeric plugin key.",
            "required": True
        },
        "name": {
            "type": "string",
            "description": "Human-readable plugin name.",
            "required": True
        },
        "description": {
            "type": "string",
            "description": "Purpose details of the plugin.",
            "required": True
        },
        "tools": {
            "type": "array",
            "description": "List of tool schema objects exposed by the plugin.",
            "required": False
        },
        "auto_discover": {
            "type": "boolean",
            "description": "If true, scans the local host for active developer services and registers them.",
            "required": False
        }
      }
}

def scan_local_services() -> list:
    """Scans standard local developer ports to discover active services."""
    common_services = [
        {"port": 2375, "name": "Docker Daemon", "type": "docker", "desc": "Local Docker container management engine"},
        {"port": 5432, "name": "PostgreSQL Database", "type": "postgres", "desc": "Local Postgres database host server"},
        {"port": 6379, "name": "Redis Cache", "type": "redis", "desc": "High-performance cache and session broker"},
        {"port": 27017, "name": "MongoDB Database", "type": "mongodb", "desc": "NoSQL document store endpoint"},
        {"port": 8080, "name": "Alternative HTTP Service", "type": "http", "desc": "Custom local application service"},
        {"port": 8000, "name": "Local API Gateway", "type": "http", "desc": "FastAPI or Django backend gateway"},
        {"port": 3000, "name": "React Dev Server", "type": "http", "desc": "Frontend modern application build platform"},
        {"port": 8501, "name": "Streamlit Dashboard", "type": "http", "desc": "Interactive machine learning visualization panel"}
    ]
    discovered = []
    for service in common_services:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)  # High-speed connection timeout check
            result = s.connect_ex(('127.0.0.1', service["port"]))
            if result == 0:
                discovered.append(service)
    return discovered

def execute(args: dict, clearance_tokens: dict) -> dict:
    """Scaffolds a compliant manifest, auto-discovers active local hooks, and registers to database."""
    plugin_id = args.get("plugin_id")
    name = args.get("name")
    description = args.get("description")
    tools = args.get("tools", [])
    auto_discover = args.get("auto_discover", True)
    
    # 1. Assert tokens
    fs_token = clearance_tokens.get("filesystem.write")
    if not fs_token:
        raise PermissionError("Missing required filesystem.write authorization to scaffold plugins.")

    discovered_services = []
    if auto_discover:
        discovered_services = scan_local_services()
        
    # If auto-discover found services, append virtual tools matching those services
    if discovered_services:
        for ds in discovered_services:
            tools.append({
                "name": f"connect_local_{ds['type']}",
                "description": f"Auto-discovered hook: Connects and interacts with {ds['name']} running on port {ds['port']}.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "port": {"type": "integer", "default": ds["port"]},
                        "action": {"type": "string", "description": "Operational action to execute against service."}
                    }
                }
            })

    # 2. Build structured manifest matching the plugin manifest schema contract
    manifest = {
        "plugin_id": plugin_id,
        "name": name,
        "version": "1.0.0",
        "description": f"{description} (Discovered Services: {len(discovered_services)})",
        "publisher": "Jarvis Scaffolder Agent",
        "capabilities": {
            "required": ["filesystem.read"]
        },
        "tools": tools,
        "event_subscriptions": []
    }
    
    # 3. Save to data/manifests
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(cwd, "data", "manifests")
    os.makedirs(target_dir, exist_ok=True)
    
    target_path = os.path.join(target_dir, f"{plugin_id}_manifest.json")
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    # 4. Save to SQL Database app_connectors table if Flask app context is active
    db_registered = False
    try:
        from flask import current_app
        if current_app:
            from models import db, AppConnector, User
            
            # Fetch default user
            user = User.query.filter_by(username='Ayush').first() or User.query.filter_by(username='Admin').first() or User.query.first()
            if user:
                connector = AppConnector.query.filter_by(user_id=user.id, provider=plugin_id).first()
                if not connector:
                    connector = AppConnector(
                        user_id=user.id,
                        provider=plugin_id,
                        is_active=True,
                        command="scaffolded",
                        args=[target_path],
                        env_vars={"discovered_ports": [ds["port"] for ds in discovered_services]},
                        scopes=["mcp_access", "filesystem.read"]
                    )
                    db.session.add(connector)
                else:
                    connector.is_active = True
                    connector.command = "scaffolded"
                    connector.args = [target_path]
                    connector.env_vars = {"discovered_ports": [ds["port"] for ds in discovered_services]}
                
                db.session.commit()
                db_registered = True
    except Exception as db_err:
        # Ignore if Flask app context isn't active
        pass

    return {
        "status": "SCAFFOLDED",
        "manifest_path": target_path,
        "manifest_payload": manifest,
        "auto_discovery_run": auto_discover,
        "discovered_services": discovered_services,
        "db_registered": db_registered
    }
