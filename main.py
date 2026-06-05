"""
Jarvis v16.0 — FastAPI Intelligence Gateway
The Central Brain Interface for Web, API, and Voice.
"""
import json
import asyncio
import logging
import os
import uuid
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from models import db, User, Conversation, Rating, AppConnector
from core.chat_engine import ChatEngine
from core.agent_engine import AgentEngine
from core.brain import JarvisBrain
from core.voice import speak
from core.git_manager import GitManager
from core.test_engine import TestEngine
from core.debug_engine import DebugEngine
from core.auto_debugger import AutoDebugger
from core.telemetry import telemetry_manager
from core.mcp_engine import mcp_engine

# ─── Initialization ───────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JARVIS Intelligence Grid v16.0")

# Enable CORS for local testing and Electron connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_templates_dir = os.path.join(config.BASE_DIR, "templates")
_static_dir = os.path.join(config.BASE_DIR, "static")
_data_dir = config.DATA_DIR
templates = Jinja2Templates(directory=_templates_dir)
templates.env.globals["csrf_token"] = lambda: "dummy_csrf_token"

app.mount("/static", StaticFiles(directory=_static_dir), name="static")
app.mount("/api/assets", StaticFiles(directory=_data_dir), name="assets")
app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "omega", "assets")), name="omega_assets")

@app.get("/favicon.svg", response_class=FileResponse)
def get_favicon():
    return FileResponse(os.path.join(_static_dir, "omega", "favicon.svg"))

# ─── Flask App Context Wrapper (for SQLAlchemy models compatibility) ────
from flask import Flask as FlaskApp
flask_app = FlaskApp("jarvis_dummy")
flask_app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(flask_app)

# Initialize database tables in dummy context if not exists
with flask_app.app_context():
    try:
        db.create_all()
        # Seed default local user (Ayush / Admin)
        admin = User.query.filter_by(username="Ayush").first()
        if not admin:
            admin = User(username="Ayush", email="ayush@jarvis.ai", tier="unlimited", credits=1000)
            db.session.add(admin)
            db.session.commit()
            logger.info("Local Admin user seeded successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite Database: {e}")

# Manifest the Brain
from core.model_manager import ModelManager
from core.knowledge_manager import KnowledgeManager

model_manager = ModelManager()
knowledge_manager = KnowledgeManager()
chat_engine = ChatEngine(model_manager, knowledge_manager)
agent_engine = AgentEngine()
brain = JarvisBrain(agent_engine)

# Manifest the Self-Healing Grid
git_manager = GitManager()
test_engine = TestEngine()
debug_engine = DebugEngine(chat_engine, git_manager, test_engine)
auto_debugger = AutoDebugger(debug_engine)

# ─── Data Models ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    convo_id: Optional[str] = "global_user"

class ToggleConnectorRequest(BaseModel):
    provider: str
    command: Optional[str] = None
    args: Optional[List[str]] = []
    env_vars: Optional[Dict[str, str]] = {}

# ─── Page Routes ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the Legacy Jarvis Executive HUD."""
    return templates.TemplateResponse(request=request, name="premium.html")

@app.get("/premium", response_class=HTMLResponse)
async def read_premium(request: Request):
    """Serve the Legacy Jarvis Executive HUD."""
    return templates.TemplateResponse(request=request, name="premium.html")

# ─── Me / User Session Endpoint ─────────────────────────────────
@app.get("/api/me")
async def get_me():
    """Returns local authenticated admin information."""
    return {
        "id": 1,
        "username": "Ayush",
        "email": "ayush@jarvis.ai",
        "is_admin": True,
        "tier": "UNLIMITED",
        "credits": 1000
    }

@app.get("/api/user/status")
async def get_user_status():
    """SaaS readout compatible with React HUD."""
    return {
        "username": "Ayush",
        "tier": "UNLIMITED",
        "credits": 1000,
        "is_unlimited": True,
        "is_admin": True
    }

# ─── Chat API (Neural Streaming) ─────────────────────────────
@app.post("/api/chat")
async def chat_endpoint(chat_req: ChatRequest):
    """Unified SSE Intelligence Endpoint."""
    trace_id = f"trc_{uuid.uuid4().hex[:6]}"
    telemetry_manager.set_trace_id(trace_id)
    telemetry_manager.add_timeline_event(f"Received user query: '{chat_req.message[:30]}...'")
    
    async def event_generator():
        start_time = time.time()
        try:
            # Wrap database-backed operations in the dummy Flask context
            with flask_app.app_context():
                user = User.query.get(1)  # Default admin user
                convo_id = chat_req.convo_id
                
                # Check for "new conversation"
                if convo_id == "global_user" or not convo_id:
                    convo_id = str(uuid.uuid4())[:8]

                # Stream synthesis from multi-agent chat engine
                logger.info(f"[{trace_id}] Activating Neural Grid Stream...")
                telemetry_manager.add_trace(f"Initiating stream for message: '{chat_req.message[:40]}'")
                
                for chunk in chat_engine.chat_stream(
                    message=chat_req.message,
                    user=user,
                    conv_id=convo_id,
                    mode="chat",
                    trace_id=trace_id
                ):
                    if chunk:
                        # Extract status prefixes and log to telemetry traces
                        if chunk.startswith("__STATUS__:"):
                            status_msg = chunk.replace("__STATUS__:", "").strip()
                            telemetry_manager.add_trace(status_msg)
                            yield f"data: {json.dumps({'chunk': '', 'status': status_msg})}\n\n"
                        elif chunk.startswith("__IMAGE__:"):
                            url = chunk.replace("__IMAGE__:", "").strip()
                            yield f"data: {json.dumps({'image': url})}\n\n"
                        elif chunk.startswith("__VIDEO__:"):
                            url = chunk.replace("__VIDEO__:", "").strip()
                            yield f"data: {json.dumps({'video': url})}\n\n"
                        else:
                            yield f"data: {json.dumps({'chunk': chunk, 'trace_id': trace_id})}\n\n"
                        await asyncio.sleep(0.01)

                latency_ms = (time.time() - start_time) * 1000.0
                telemetry_manager.update_api_latency("/api/chat", latency_ms)
                telemetry_manager.add_timeline_event("Response synthesis fully rendered")
                
                yield f"data: {json.dumps({'done': True, 'conversation_id': convo_id})}\n\n"
            
        except Exception as e:
            logger.error(f"Brain Failure: {e}")
            telemetry_manager.add_trace(f"Breach: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# ─── Conversations / Memory Thread Routes ─────────────────────────
@app.get("/api/conversations")
async def list_conversations():
    """Retrieve full list of active SQLite memory threads."""
    start_time = time.time()
    with flask_app.app_context():
        try:
            res = chat_engine.list_conversations(user_id=1)
            telemetry_manager.update_api_latency("/api/conversations", (time.time() - start_time) * 1000.0)
            return res
        except Exception as e:
            logger.error(f"Error fetching threads: {e}")
            return []

@app.get("/api/conversations/{convo_id}")
async def get_conversation(convo_id: str):
    """Retrieve a single thread with complete history."""
    start_time = time.time()
    with flask_app.app_context():
        try:
            conv = chat_engine.get_conversation(convo_id)
            if not conv:
                raise HTTPException(status_code=404, detail="Memory thread not found")
            telemetry_manager.update_api_latency("/api/conversations", (time.time() - start_time) * 1000.0)
            return conv
        except Exception as e:
            logger.error(f"Error fetching thread {convo_id}: {e}")
            raise HTTPException(status_code=404, detail="Memory thread not found")

@app.delete("/api/conversations/{convo_id}")
async def delete_conversation(convo_id: str):
    """Purge a conversation from SQLite database and local memory."""
    with flask_app.app_context():
        try:
            conv = Conversation.query.get(convo_id)
            if conv:
                db.session.delete(conv)
                db.session.commit()
                telemetry_manager.add_trace(f"Purged memory thread ID: {convo_id}")
                return {"status": "success", "message": f"Thread {convo_id} purged."}
            raise HTTPException(status_code=404, detail="Thread not found")
        except Exception as e:
            logger.error(f"Error purging thread {convo_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# ─── Telemetry Statistics Route (Real analytics) ───────────────────
@app.get("/api/system/stats")
async def get_system_stats():
    """Telemetry analytics gateway for the React dashboard HUD."""
    start_t = time.time()
    payload = telemetry_manager.get_telemetry_payload()
    telemetry_manager.update_api_latency("/api/system/stats", (time.time() - start_t) * 1000.0)
    return payload

# ─── MCP Connector Routes ──────────────────────────────────────────
@app.get("/api/connectors")
async def get_connectors():
    """Get all active connectors for the current user."""
    with flask_app.app_context():
        # Default local user is 1 (Ayush)
        connectors = AppConnector.query.filter_by(user_id=1).all()
        return {
            "status": "success",
            "connectors": [{
                "id": c.id,
                "provider": c.provider,
                "is_active": c.is_active,
                "scopes": c.scopes,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            } for c in connectors]
        }

@app.post("/api/connectors/toggle")
async def toggle_connector(req: ToggleConnectorRequest):
    """Toggle connection status for an MCP provider."""
    provider = req.provider
    command = req.command
    args = req.args
    env_vars = req.env_vars
    
    if not provider:
        raise HTTPException(status_code=400, detail="Provider is required.")
        
    with flask_app.app_context():
        connector = AppConnector.query.filter_by(user_id=1, provider=provider).first()
        try:
            if connector:
                connector.is_active = not connector.is_active
                if connector.is_active:
                    if connector.command:
                        await mcp_engine.connect_server(provider, connector.command, connector.args, connector.env_vars)
                else:
                    await mcp_engine.disconnect_server(provider)
            else:
                # Create new connection
                connector = AppConnector(
                    user_id=1,
                    provider=provider,
                    is_active=True,
                    command=command,
                    args=args,
                    env_vars=env_vars,
                    scopes=["mcp_access"]
                )
                db.session.add(connector)
                if command:
                    await mcp_engine.connect_server(provider, command, args, env_vars)
                
            db.session.commit()
            return {
                "status": "success",
                "provider": connector.provider,
                "is_active": connector.is_active,
                "scopes": connector.scopes
            }
        except Exception as e:
            logger.error(f"Failed to toggle MCP server: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/tools")
async def get_mcp_tools():
    """Returns the list of tools available from connected MCP servers."""
    tools = await mcp_engine.get_raw_tools()
    return tools

# ─── Skills Layer Endpoint ───────────────────────────────────────
@app.get("/api/skills/list")
async def get_skills_list():
    """Retrieve registered self-healing skills manifest."""
    try:
        from core.skills_registry import skills_registry
        skills_registry.discover_and_load_skills()
        return {
            "status": "success",
            "skills": [s["manifest"] for s in skills_registry.skills.values()]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ─── File Upload Ingestion Route ──────────────────────────────────
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload dynamic code scripts or documents for context injection."""
    try:
        from werkzeug.utils import secure_filename
        os.makedirs(config.UPLOAD_DIR, exist_ok=True)
        
        filename = f"up_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
        filepath = os.path.join(config.UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil_contents = await file.read()
            buffer.write(shutil_contents)
            
        telemetry_manager.add_trace(f"Ingested file: '{file.filename}'")
        return {
            "status": "success",
            "filename": filename,
            "url": f"/api/assets/uploads/{filename}"
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Voice API (Speech Synthesis) ─────────────────────────────────
@app.post("/api/voice")
async def voice_endpoint(chat_req: ChatRequest):
    """Synthesize speech audio for the requested response text."""
    try:
        # 1. Synthesize text response
        with flask_app.app_context():
            user = User.query.get(1)
            text_response = ""
            for chunk in chat_engine.chat_stream(chat_req.message, user=user):
                if chunk and not chunk.startswith("__"):
                    text_response += chunk

        # 2. Convert to speech audio
        voice_path = await speak(text_response)
        return FileResponse(voice_path, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Voice generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── Dynamic Image Generation API ───────────────────────────────
class ImageRequest(BaseModel):
    prompt: str

@app.post("/api/generate_image")
async def generate_image_endpoint(req: ImageRequest):
    """Generate image via visual engines."""
    try:
        from core.image_engine import ImageGenerator
        gen = ImageGenerator()
        res = gen.generate(req.prompt)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Self-Healing Activation ─────────────────────────────────
def auto_heal_loop():
    """Background neural health maintenance."""
    while True:
        try:
            logger.info("🧠 Auto-Heal: Beginning system scan...")
            auto_debugger.run_once()
        except Exception as e:
            logger.error(f"Auto-Heal Critical Failure: {e}")
        time.sleep(60) # Scan every minute

# Launch Self-Healing in daemon thread
import threading
threading.Thread(target=auto_heal_loop, daemon=True).start()

# ─── Lifespan / Startup ──────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("  JARVIS v16.0 — GEMINI-POWERED CENTRAL BRAIN ONLINE")
    logger.info(f"  SYSTEM TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Auto-boot active MCP connectors on startup
    with flask_app.app_context():
        try:
            active_connectors = AppConnector.query.filter_by(is_active=True).all()
            for c in active_connectors:
                logger.info(f"Auto-booting active MCP connector: {c.provider}")
                asyncio.create_task(mcp_engine.connect_server(c.provider, c.command, c.args, c.env_vars))
        except Exception as e:
            logger.error(f"Failed to auto-boot active MCP connectors: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT)
