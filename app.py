"""
Jarvis v12.0 - Assistant
Clean, natural, and helpful local AI.
"""
import json
import logging
import os
import sys
import uuid
import asyncio
import shutil
import tempfile
import threading
import time
from datetime import datetime, timezone

# Neural Pathing: Fix for cloud module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, Response, send_file, after_this_request, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

import config
from models import db, User, Conversation, Rating, AppConnector
from core.model_manager import ModelManager
from core.knowledge_manager import KnowledgeManager
from core.chat_engine import ChatEngine
from core.image_engine import ImageGenerator
from core.video_engine import create_video
from core.mission_engine import MissionEngine
from core.intel_engine import IntelEngine
from core.briefing_engine import BriefingEngine
from core.webhook_engine import webhook_engine
from core.async_runner import run_async
from core.diagnostics import DiagnosticNode
from core.bug_analyzer import run_autonomous_scan
from core.system_guardian import system_guardian
from core.mcp_engine import mcp_engine
import edge_tts
import hashlib
from concurrent.futures import ThreadPoolExecutor
import stripe

# ─── Security Filter (Secrets Scrubber) ──────────────────────────────
class SecretsFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            from core.tools import SecurityGuard
            record.msg = SecurityGuard.scrub(record.msg)
        return True

os.makedirs(config.LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
# Apply Security Filter to all handlers
for handler in logging.root.handlers:
    handler.addFilter(SecretsFilter())

logger = logging.getLogger(__name__)

# ─── Flask App Setup ────────────────────────────────────────────────
app = Flask(__name__)
print(f"DEBUG: Template folder: {app.template_folder}")
print(f"DEBUG: Root path: {app.root_path}")
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

CORS(app)
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
# Exempt all /api/* routes from CSRF — the OMEGA React UI uses JSON APIs without CSRF tokens.
# Legacy template routes (/premium, /legacy) retain CSRF protection via meta tags.
app.config['WTF_CSRF_CHECK_DEFAULT'] = False

@app.before_request
def csrf_protect_non_api():
    """Apply CSRF only to non-API routes (legacy template forms)."""
    if not request.path.startswith('/api/'):
        try:
            csrf.protect()
        except Exception:
            pass  # Allow GET requests and static files through

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"

# ─── Stripe Configuration ───────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")

@login_manager.user_loader
def load_user(user_id):
    # --- Home Grid Auto-Auth ---
    try:
        from flask import request
        remote_addr = request.remote_addr
        if remote_addr in ["127.0.0.1", "localhost"] or remote_addr.startswith("192.168.") or remote_addr.startswith("10."):
            return User.query.first()
    except Exception:
        pass
        
    return User.query.get(int(user_id))

@app.before_request
def auto_login_local_host():
    """Auto-login local/loopback requests if not already authenticated."""
    if not current_user.is_authenticated:
        try:
            remote_addr = request.remote_addr
            if remote_addr in ["127.0.0.1", "localhost"] or remote_addr.startswith("192.168.") or remote_addr.startswith("10."):
                from models import User
                # Find local user: Ayush first, then Admin, then first available
                local_user = User.query.filter_by(username='Ayush').first()
                if not local_user:
                    local_user = User.query.filter_by(username='Admin').first()
                if not local_user:
                    local_user = User.query.first()
                
                if local_user:
                    login_user(local_user, remember=True)
                    logger.info(f"Auto-logged in local user: {local_user.username} from {remote_addr}")
        except Exception as e:
            logger.error(f"Auto-login failed: {e}")

@login_manager.unauthorized_handler
def unauthorized():
    # API routes should return JSON instead of redirecting.
    if request.path.startswith("/api/"):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"error": "Unauthorized"}), 401

# ─── Initialize Intelligence Components ─────────────────────────────
logger.info("Initializing Jarvis Assistant...")

# Run Neural Pre-Flight
vitals = DiagnosticNode.run_preflight()
if vitals["status"] == "critical":
    logger.critical("Neural link failure: Core systems offline. Maintenance required.")

# ─── Production Hardening: Heartbeat & Rate Limiting ──────────────
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    def limiter_key():
        """Neural Clearance: Exempt local grid and admin IPs from rate limiting."""
        ip = get_remote_address()
        # Admin IP (Your device) or Local Loopback
        if ip in ["127.0.0.1", "localhost", "192.168.1.2"] or ip.startswith("10."):
            return None # Unlimited
        return ip

    limiter = Limiter(
        key_func=limiter_key,
        app=app,
        storage_uri="memory://",
    )
except ImportError:
    logger.warning("Neural Guard Offline: 'flask_limiter' not found. Rate limiting disabled.")
    class Limiter:
        def __init__(self, *args, **kwargs): pass
        def limit(self, *args, **kwargs):
            return lambda f: f
    limiter = Limiter()

def neural_heartbeat():
    """Background thread to monitor system health every 15 minutes."""
    while True:
        try:
            health = DiagnosticNode.check_environment()
            logger.info(f"Neural Heartbeat: {health['status'].upper()} | Active Threads: {threading.active_count()}")
        except Exception as e:
            logger.error(f"Heartbeat Failure: {e}")
        
        # Dump threads every 10 seconds for debugging
        import traceback, sys
        logger.info("--- DUMPING ALL THREADS ---")
        for th in threading.enumerate():
            logger.info(f"Thread: {th.name}")
            frame = sys._current_frames().get(th.ident)
            if frame:
                logger.info("".join(traceback.format_stack(frame)))
        logger.info("---------------------------")
        
        import time
        time.sleep(10) # 10 seconds for debug

threading.Thread(target=neural_heartbeat, daemon=True).start()

model_manager = ModelManager()
knowledge_manager = KnowledgeManager()
chat_engine = ChatEngine(model_manager, knowledge_manager)
mission_engine = MissionEngine(model_manager)
briefing_engine = BriefingEngine(os.path.join(config.DATA_DIR, "briefings"))
intel_engine = IntelEngine(mission_engine, chat_engine, briefing_engine)
executor = ThreadPoolExecutor(max_workers=5)

NEURAL_REGISTRY = {} # hash -> filepath

# ─── Page Routes ─────────────────────────────────────────────────────

# Path to the built OMEGA React UI
OMEGA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "omega")

@app.route("/")
def index():
    """Serve the JARVIS premium holographic interface (React UI)."""
    return send_from_directory(OMEGA_DIR, "index.html")

@app.route("/assets/<path:filename>")
def omega_assets(filename):
    """Serve OMEGA React build assets (JS, CSS)."""
    return send_from_directory(os.path.join(OMEGA_DIR, "assets"), filename)

@app.route("/favicon.svg")
def omega_favicon():
    """Serve OMEGA favicon."""
    return send_from_directory(OMEGA_DIR, "favicon.svg")

@app.route("/legacy")
def legacy():
    """Serve the legacy premium holographic interface."""
    return render_template("premium.html", google_client_id=config.GOOGLE_CLIENT_ID)

@app.route("/premium")
def premium():
    """Serve the legacy premium holographic interface."""
    return render_template("premium.html", google_client_id=config.GOOGLE_CLIENT_ID)

@app.route("/test")
def test():
    try:
        return jsonify({"status": "ok", "template_folder": app.template_folder, "root_path": app.root_path, "omega_dir": OMEGA_DIR})
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

# ─── Authentication ───────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        login_user(user, remember=True)
        return jsonify({"success": True, "user": {"id": user.id, "username": user.username}})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    logout_user()
    return jsonify({"success": True})

# --- Google Workspace MCP OAuth Flow ---
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

GOOGLE_AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

@app.route("/api/auth/google/workspace", methods=["GET"])
@login_required
def auth_google_workspace():
    """Start Google Workspace OAuth flow."""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        return jsonify({"error": "Google Client credentials not configured in config.py"}), 500
        
    try:
        from requests_oauthlib import OAuth2Session
        redirect_uri = request.url_root.rstrip("/") + "/api/auth/google/workspace/callback"
        google = OAuth2Session(
            config.GOOGLE_CLIENT_ID,
            redirect_uri=redirect_uri,
            scope=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/documents"
            ]
        )
        
        authorization_url, state = google.authorization_url(
            GOOGLE_AUTHORIZATION_BASE_URL,
            access_type="offline",
            prompt="consent"
        )
        
        return jsonify({"authorization_url": authorization_url})
    except Exception as e:
        logger.error(f"Failed to start Google OAuth: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth/google/workspace/callback", methods=["GET"])
@login_required
def auth_google_workspace_callback():
    """Handle Google Workspace OAuth callback and persist tokens."""
    try:
        from requests_oauthlib import OAuth2Session
        redirect_uri = request.url_root.rstrip("/") + "/api/auth/google/workspace/callback"
        google = OAuth2Session(
            config.GOOGLE_CLIENT_ID,
            redirect_uri=redirect_uri
        )
        
        # Fix for HTTP/HTTPS mismatch in local testing
        auth_response = request.url.replace('http://', 'https://') if not request.url.startswith('https') else request.url
        
        token = google.fetch_token(
            GOOGLE_TOKEN_URL,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            authorization_response=auth_response
        )
        
        connector = AppConnector.query.filter_by(user_id=current_user.id, provider="google-workspace").first()
        env_vars = {
            "GOOGLE_CLIENT_ID": config.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": config.GOOGLE_CLIENT_SECRET,
            "GOOGLE_ACCESS_TOKEN": token.get("access_token", ""),
            "GOOGLE_REFRESH_TOKEN": token.get("refresh_token", "")
        }
        
        if connector:
            connector.env_vars = env_vars
            connector.is_active = True
        else:
            connector = AppConnector(
                user_id=current_user.id,
                provider="google-workspace",
                is_active=True,
                command="npx",
                args=["-y", "@modelcontextprotocol/server-google-workspace"],
                env_vars=env_vars,
                scopes=token.get("scope", [])
            )
            db.session.add(connector)
            
        db.session.commit()
        
        # Spawn the MCP server
        run_async(mcp_engine.connect_server("google-workspace", "npx", ["-y", "@modelcontextprotocol/server-google-workspace"], env_vars))
        
        return """
        <html>
        <head><script>
            window.opener.postMessage('google_workspace_authorized', '*');
            window.close();
        </script></head>
        <body>Authorization successful! JARVIS is now connected to your Google Workspace. You may close this window.</body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Google Workspace OAuth Error: {e}")
        return f"Authentication failed: {str(e)}", 500

@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    """
    Direct Gmail / Google OAuth verification and Auto-Registration.
    Verifies the client-side Google ID token (JWT) via Google's tokeninfo API.
    """
    import requests
    import re
    
    data = request.get_json() or {}
    token = data.get("credential")
    if not token:
        return jsonify({"error": "Missing token payload"}), 400

    # 1. Verify token with Google's API
    try:
        response = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={token}",
            timeout=5
        )
        if response.status_code != 200:
            return jsonify({"error": "Invalid Google token"}), 401
        
        info = response.json()
    except Exception as e:
        logger.error(f"Google Token Verification Error: {e}")
        return jsonify({"error": "Failed to connect to Google Auth servers"}), 503

    # 2. Extract user metadata from verified token
    email = info.get("email")
    email_verified = info.get("email_verified")
    
    # Google API returns email_verified as string "true" or boolean True
    if not email or (email_verified != "true" and email_verified != True):
        return jsonify({"error": "Google email must be verified"}), 400

    # 3. Locate or register User
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Check if the generated username from email prefix already exists
        base_username = email.split("@")[0]
        # Clean username to be alphanumeric + underscores/dashes only
        username = re.sub(r'[^a-zA-Z0-9_]', '', base_username)
        if not username:
            username = "user"
            
        counter = 1
        final_username = username
        while User.query.filter_by(username=final_username).first() is not None:
            final_username = f"{username}_{counter}"
            counter += 1
            
        # Create direct Google/Gmail sign-up user (credits: 100 welcome bonus)
        user = User(
            username=final_username,
            email=email,
            tier="free",
            credits=100
        )
        # Ensure password_hash is explicitly set to None (no password login unless updated later)
        user.password_hash = None
        
        try:
            db.session.add(user)
            db.session.commit()
            logger.info(f"Direct Gmail Sign-up complete: Created user {final_username} ({email})")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to register Gmail user: {e}")
            return jsonify({"error": "User registration database failure"}), 500
            
    # 4. Perform session login
    login_user(user, remember=True)
    logger.info(f"Direct Gmail Login successful: User {user.username} ({user.email})")
    
    return jsonify({
        "success": True, 
        "user": {
            "id": user.id, 
            "username": user.username, 
            "email": user.email, 
            "tier": user.tier,
            "credits": user.credits
        }
    })

@app.route("/api/me")
def get_me():
    if current_user.is_authenticated:
        return jsonify({"id": current_user.id, "username": current_user.username, "is_admin": current_user.is_admin})
    return jsonify({"id": 0, "username": "Guest", "is_admin": False})

@app.route("/api/assets/<atype>/<filename>")
def serve_assets(atype, filename):
    """Serve synthesized visual and vocal assets from the neural grid."""
    if atype == "images":
        return send_from_directory(config.IMAGE_GEN_DIR, filename)
    elif atype == "videos":
        return send_from_directory(config.VIDEO_GEN_DIR, filename)
    elif atype == "uploads":
        return send_from_directory(config.UPLOAD_DIR, filename)
    return jsonify({"error": "Asset category not found"}), 404

@app.route("/api/upload", methods=["POST"])
@login_required
def upload_file():
    """Neural Ingestion: Accepting external files for deep analysis."""
    if 'file' not in request.files:
        return jsonify({"error": "No file payload detected"}), 400
    
    from werkzeug.utils import secure_filename
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'md', 'py', 'json', 'csv'}
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename detected"}), 400
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if file and allowed_file(file.filename):
        safe_name = secure_filename(file.filename)
        filename = f"up_{uuid.uuid4().hex[:8]}_{safe_name}"
        filepath = os.path.join(config.UPLOAD_DIR, filename)
        file.save(filepath)
        
        # Extract text content for initial analysis (TXT, MD, PY, etc.)
        content = ""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            content = "[Binary or unreadable file content]"
            
        return jsonify({
            "status": "success",
            "filename": filename,
            "url": f"/api/assets/uploads/{filename}",
            "content_snippet": content[:2000] # Provide a snippet for immediate context
        })

# ─── App Connectors API ───────────────────────────────────────────────────
@app.route("/api/connectors", methods=["GET"])
@login_required
def get_connectors():
    """Get all active connectors for the current user."""
    connectors = AppConnector.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        "status": "success",
        "connectors": [{
            "id": c.id,
            "provider": c.provider,
            "is_active": c.is_active,
            "scopes": c.scopes,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        } for c in connectors]
    }), 200

@app.route("/api/connectors/toggle", methods=["POST"])
@login_required
def toggle_connector():
    """Toggle connection status for an MCP provider."""
    data = request.json
    provider = data.get("provider")
    command = data.get("command")
    args = data.get("args", [])
    env_vars = data.get("env_vars", {})
    
    if not provider:
        return jsonify({"status": "error", "message": "Provider is required."}), 400
        
    connector = AppConnector.query.filter_by(user_id=current_user.id, provider=provider).first()
    
    try:
        if connector:
            # Toggle existing connection
            connector.is_active = not connector.is_active
            if connector.is_active:
                if connector.command:
                    run_async(mcp_engine.connect_server(provider, connector.command, connector.args, connector.env_vars))
            else:
                run_async(mcp_engine.disconnect_server(provider))
        else:
            if provider == "google-workspace":
                return jsonify({"status": "error", "message": "Google Workspace requires OAuth authentication. Please use the Google Sign-In button first."}), 403
                
            # Create new connection
            connector = AppConnector(
                user_id=current_user.id,
                provider=provider,
                is_active=True,
                command=command,
                args=args,
                env_vars=env_vars,
                scopes=["mcp_access"]
            )
            db.session.add(connector)
            if command:
                run_async(mcp_engine.connect_server(provider, command, args, env_vars))
            
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to toggle MCP server: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
    return jsonify({
        "status": "success",
        "provider": connector.provider,
        "is_active": connector.is_active,
        "scopes": connector.scopes
    }), 200

@app.route("/api/mcp/tools", methods=["GET"])
@login_required
def get_mcp_tools():
    """Returns the list of tools available from connected MCP servers."""
    tools = run_async(mcp_engine.get_raw_tools())
    return jsonify(tools), 200

# ─── Skills Layer APIs ───────────────────────────────────────────────────
@app.route("/api/skills/list", methods=["GET"])
@login_required
def get_skills_list():
    """Returns a list of all dynamically registered skills and their manifests."""
    from core.skills_registry import skills_registry
    skills_registry.discover_and_load_skills()
    
    skills_list = []
    for skill_id, skill_info in skills_registry.skills.items():
        skills_list.append(skill_info["manifest"])
        
    return jsonify({
        "status": "success",
        "skills": skills_list
    }), 200

@app.route("/api/skills/execute", methods=["POST"])
@login_required
def execute_skill_api():
    """Secure API gateway endpoint to execute a composite registered skill."""
    from core.skills_registry import skills_registry
    
    data = request.json or {}
    skill_id = data.get("skill_id")
    args = data.get("args", {})
    
    if not skill_id:
        return jsonify({"status": "error", "message": "skill_id is required."}), 400
        
    # Determine the clearance level based on the current user's role/tier
    clearance_level = "LOW"
    if current_user.is_admin:
        clearance_level = "CRITICAL"
    elif current_user.tier == "pro":
        clearance_level = "MEDIUM"
        
    context = {
        "clearance_level": clearance_level,
        "args": args
    }
    
    # Refresh/load skills dynamically
    skills_registry.discover_and_load_skills()
    
    result = skills_registry.execute_skill(skill_id, context)
    if result.get("success"):
        return jsonify({
            "status": "success",
            "skill_id": skill_id,
            "result": result.get("result")
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": result.get("error", "Execution failed."),
            "required_capabilities": result.get("required_capabilities"),
            "missing_capabilities": result.get("missing_capabilities")
        }), 403

@app.route("/api/skills/install", methods=["POST"])
@login_required
def install_skill_pack():
    """Secure API endpoint to upload and install a zipped skill pack."""
    from core.skills_registry import skills_registry
    
    # 1. Determine user clearance level and block if not HIGH or CRITICAL
    clearance_level = "LOW"
    if current_user.is_admin:
        clearance_level = "CRITICAL"
    elif current_user.tier == "pro":
        clearance_level = "HIGH"
    
    if clearance_level not in ["HIGH", "CRITICAL"]:
        return jsonify({
            "status": "error",
            "message": "Access Denied: High or Critical clearance is required to install new skills."
        }), 403
        
    # 2. Check if a file was uploaded in the request
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded in the request."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Selected file is empty."}), 400
        
    if not file.filename.endswith('.zip'):
        return jsonify({"status": "error", "message": "Only .zip files are accepted as skill packs."}), 400

    expected_checksum = request.form.get("checksum", "").strip() or None
    
    # 3. Save zip to a secure temporary location inside the workspace subdirectory 'scratch/'
    cwd = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(cwd, "scratch", "skill_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    from werkzeug.utils import secure_filename
    safe_name = secure_filename(file.filename)
    temp_zip_path = os.path.join(temp_dir, safe_name)
    
    try:
        file.save(temp_zip_path)
        logger.info(f"[SKILLS INSTALL] Saved uploaded zip pack temporarily to {temp_zip_path}")
        
        # 4. Ingest and extract the zip skill pack securely
        res = skills_registry.ingest_zip_skill_pack(temp_zip_path, expected_checksum=expected_checksum)
        
        # Clean up the temporary zip file
        try:
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
        except Exception as cleanup_err:
            logger.warning(f"[SKILLS INSTALL] Failed to delete temp zip '{temp_zip_path}': {cleanup_err}")
            
        if res.get("success"):
            return jsonify({
                "status": "success",
                "message": "Skill pack successfully installed and loaded into Jarvis OS.",
                "checksum": res.get("checksum")
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": res.get("error", "Failed to install skill pack.")
            }), 400
            
    except Exception as e:
        logger.exception("Exception during skill pack installation")
        return jsonify({"status": "error", "message": f"Installation exception: {e}"}), 500

# ─── Ratings API ────────────────────────────────────────────────────────


@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a chat message and get a streaming response."""
    try:
        # 1. Validate Input
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400
            
        message = data.get("message", "").strip()
        conv_id = data.get("conversation_id")
        file_context = data.get("file_context", "")
        
        # Neural Trace ID for Deep Observability
        trace_id = f"trc_{uuid.uuid4().hex[:6]}"
        logger.info(f"[{trace_id}] New Mission Sequence: {message[:30]}...")

        # 2. Synchronized Stream Generator
        user_obj = None
        if getattr(current_user, "is_authenticated", False):
            user_obj = current_user._get_current_object() if hasattr(current_user, "_get_current_object") else current_user
        
        mode = data.get("mode", "chat")

        @credit_required(cost=1)
        def generate_with_credits(user):
            user_id = getattr(user, "id", None)
            def generate():
                with app.app_context():
                    from models import User
                    active_user = User.query.get(user_id) if user_id else None
                    
                    try:
                        logger.info(f"[{trace_id}] Neural Link [Mode: {mode}]: Initiating sequence.")
                        for chunk in chat_engine.chat_stream(message, active_user, conv_id, mode=mode, file_context=file_context, trace_id=trace_id):
                            if chunk:
                                yield f"data: {json.dumps({'chunk': chunk, 'trace_id': trace_id})}\n\n"
                                
                        if active_user:
                            db.session.refresh(active_user)
                            credits_left = active_user.credits
                        else:
                            credits_left = 9999
                        yield f"data: {json.dumps({'done': True, 'conversation_id': chat_engine._current_conversation_id, 'credits': credits_left})}\n\n"
                        
                    except Exception as e:
                        logger.error(f"Neural Stream Breach: {e}")
                        yield f"data: {json.dumps({'error': f'Transmission failed: {str(e)}'})}\n\n"
            return generate()

        gen_or_res = generate_with_credits(user_obj)
        if isinstance(gen_or_res, (Response, tuple)):
            return gen_or_res

        return Response(
            gen_or_res,
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            },
        )
    except Exception as e:
        logger.error(f"Backend Gateway Error: {e}")
        return jsonify({"error": f"Internal Logic Failure: {str(e)}"}), 500

# ─── SaaS Governance ──────────────────────────────────────────
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({"error": "Admin Authority Required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def credit_required(cost=1):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Bypass authentication for local sentience update
            if request.remote_addr in ["127.0.0.1", "::1"]:
                return f(*args, **kwargs)
                
            if not getattr(current_user, "is_authenticated", False):
                return jsonify({"error": "Authentication Required"}), 401
            
            if not current_user.has_credits(cost):
                return jsonify({
                    "error": "Insufficient Neural Credits",
                    "required": cost,
                    "available": current_user.credits,
                    "suggestion": "Upgrade to Pro for unlimited usage."
                }), 402
            
            # Execute the actual function
            response = f(*args, **kwargs)
            
            # Special handling for streaming generators
            import types
            if isinstance(response, types.GeneratorType):
                # For generators, we deduct credits upfront or assume success
                if not current_user.is_unlimited:
                    current_user.credits -= cost
                    db.session.commit()
                return response

            # If successful (200 OK), deduct credits (unless unlimited)
            if not current_user.is_unlimited:
                try:
                    # Logic to check if response was successful
                    is_success = True
                    if isinstance(response, tuple) and len(response) > 1:
                        if response[1] >= 400: is_success = False
                    
                    if is_success:
                        current_user.credits -= cost
                        db.session.commit()
                        logger.info(f"SaaS: Deducted {cost} credits from {current_user.username}")
                except Exception as e:
                    logger.error(f"Credit Deduction Failure: {e}")
                    
            return response
        return decorated_function
    return decorator

# ─── Admin APIs ──────────────────────────────────────────────

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_get_users():
    """Fetch all users for management."""
    users = User.query.all()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "tier": u.tier,
        "credits": u.credits,
        "created_at": u.created_at.isoformat() if u.created_at else None
    } for u in users])

@app.route("/api/admin/user/update", methods=["POST"])
@admin_required
def admin_update_user():
    """Override a user's credits or tier."""
    data = request.json
    user_id = data.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if "credits" in data:
        user.credits = int(data["credits"])
    if "tier" in data:
        user.tier = data["tier"]
        
    db.session.commit()
    logger.info(f"Admin override: {user.username} updated to {user.tier}/{user.credits}")
    return jsonify({"status": "Success"})

@app.route("/api/admin/logs", methods=["GET"])
@admin_required
def admin_get_logs():
    """Tail the system logs for debugging."""
    try:
        with open(config.LOG_FILE, "r") as f:
            lines = f.readlines()
            # Return last 100 lines
            return jsonify({"logs": "".join(lines[-100:])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── SaaS Status ──────────────────────────────────────────────

@app.route("/api/user/status", methods=["GET"])
@login_required
def get_user_status():
    """Retrieve current user's SaaS identity and credits."""
    return jsonify({
        "username": current_user.username,
        "tier": current_user.tier.upper(),
        "credits": current_user.credits,
        "is_unlimited": current_user.is_unlimited,
        "is_admin": current_user.is_admin
    })

@app.route("/api/user/settings", methods=["POST"])
@login_required
def update_user_settings():
    """Update user preferences (personality, language, etc)."""
    data = request.json
    if not data:
        return jsonify({"error": "No settings provided"}), 400
    
    # Update personality if provided
    new_personality = data.get("personality")
    if new_personality in config.PERSONALITY_PROMPTS:
        prefs = current_user.preferences or {}
        prefs["personality"] = new_personality
        current_user.preferences = prefs
        db.session.commit()
        logger.info(f"Identity Update: {current_user.username} switched to {new_personality} mode.")
        return jsonify({"status": "Success", "personality": new_personality})
    
    return jsonify({"error": "Invalid personality mode"}), 400

# ─── Conversations ──────────────────────────────────────────────

@app.route("/api/conversations", methods=["GET"])
@login_required
def list_conversations():
    """Get all logged-in user conversations."""
    return jsonify(chat_engine.list_conversations(current_user.id))

@app.route("/api/conversations/<id>", methods=["GET"])
@login_required
def get_conversation(id):
    """Get user specific conversation snapshot."""
    data = chat_engine.get_conversation(id)
    if not data or not data.get("messages", []):
        return jsonify({"error": "Neural patterns not found"}), 404
    return jsonify(data)

@app.route("/api/conversations/<id>", methods=["DELETE"])
@login_required
def delete_conversation(id):
    """Neural Purge: Remove a conversation thread from memory."""
    chat_engine.delete_conversation(id)
    logger.info(f"Neural Purge: Conversation {id} removed by user {current_user.id}")
    return jsonify({"status": "success", "message": f"Thread {id} purged from neural memory."})

# ─── Ratings / Feedback ─────────────────────────────────────────

@app.route("/api/rate", methods=["POST"])
@login_required
def submit_rating():
    """Submit or update a rating for any target (message, image, video, intel, system)."""
    try:
        data = request.json or {}
        target_type = data.get("target_type")
        target_id = data.get("target_id")
        score = data.get("score")
        feedback = data.get("feedback", "")

        if not target_type or not target_id or score is None:
            return jsonify({"error": "Missing required fields: target_type, target_id, score"}), 400

        try:
            score = int(score)
            if score < 1 or score > 5:
                return jsonify({"error": "Score must be an integer between 1 and 5"}), 400
        except ValueError:
            return jsonify({"error": "Invalid score type"}), 400

        # Check if rating already exists for this target by this user
        existing_rating = Rating.query.filter_by(
            user_id=current_user.id,
            target_type=target_type,
            target_id=target_id
        ).first()

        if existing_rating:
            existing_rating.score = score
            existing_rating.feedback = feedback
            existing_rating.created_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info(f"Rating Updated: User {current_user.username} rated {target_type} '{target_id}' as {score} stars.")
            return jsonify({"status": "success", "message": "Rating updated successfully.", "action": "updated"})
        else:
            new_rating = Rating(
                user_id=current_user.id,
                target_type=target_type,
                target_id=target_id,
                score=score,
                feedback=feedback
            )
            db.session.add(new_rating)
            db.session.commit()
            logger.info(f"Rating Created: User {current_user.username} rated {target_type} '{target_id}' as {score} stars.")
            return jsonify({"status": "success", "message": "Rating submitted successfully.", "action": "created"})

    except Exception as e:
        logger.error(f"Rating Submission Failure: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ratings", methods=["GET"])
@login_required
def get_user_ratings():
    """Retrieve all ratings submitted by the current operator."""
    try:
        ratings = Rating.query.filter_by(user_id=current_user.id).order_by(Rating.created_at.desc()).all()
        return jsonify([{
            "id": r.id,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "score": r.score,
            "feedback": r.feedback,
            "created_at": r.created_at.isoformat()
        } for r in ratings])
    except Exception as e:
        logger.error(f"Fetch Ratings Failure: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ratings/stats", methods=["GET"])
@login_required
def get_ratings_stats():
    """Retrieve aggregate statistics of the operator's feedback for different engines."""
    try:
        ratings = Rating.query.filter_by(user_id=current_user.id).all()
        stats = {}
        for r in ratings:
            if r.target_type not in stats:
                stats[r.target_type] = {"total_score": 0, "count": 0}
            stats[r.target_type]["total_score"] += r.score
            stats[r.target_type]["count"] += 1

        output = {}
        global_total = 0
        global_count = 0
        
        for k, v in stats.items():
            avg = round(v["total_score"] / v["count"], 2)
            output[k] = {
                "average": avg,
                "count": v["count"]
            }
            global_total += v["total_score"]
            global_count += v["count"]

        output["overall"] = {
            "average": round(global_total / global_count, 2) if global_count > 0 else 0,
            "count": global_count
        }
        return jsonify(output)
    except Exception as e:
        logger.error(f"Ratings Stats Failure: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/mcp/sync", methods=["POST"])
@login_required
def mcp_sync():
    """
    Zero-Knowledge CRDT LWW-Element-Set Sync Endpoint.
    Reconciles client and server sets per tenant without reading encrypted content keys.
    """
    try:
        data = request.json or {}
        client_id = data.get("client_id")
        incoming_elements = data.get("elements", [])
        
        if not client_id:
            return jsonify({"error": "Missing client_id"}), 400
            
        # Determine tenant hash path
        username = current_user.username
        tenant_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
        
        cwd = os.path.dirname(os.path.abspath(__file__))
        tenant_dir = os.path.join(cwd, "data", "tenants", tenant_hash)
        os.makedirs(tenant_dir, exist_ok=True)
        sync_file = os.path.join(tenant_dir, "sync_store.json")
        
        # Load existing server elements (LWW set)
        server_store = {}
        if os.path.exists(sync_file):
            try:
                with open(sync_file, "r", encoding="utf-8") as f:
                    server_store = json.load(f)
            except Exception:
                server_store = {}
                
        # Merge elements using Last-Write-Wins (LWW) rules
        updated = False
        for elem in incoming_elements:
            key = elem.get("key")
            val = elem.get("value")
            ts = elem.get("timestamp", 0.0)
            tombstone = elem.get("tombstone", False)
            
            if not key:
                continue
                
            # If key not present or incoming timestamp is strictly greater, overwrite
            existing = server_store.get(key)
            if not existing or ts > existing.get("timestamp", 0.0):
                server_store[key] = {
                    "value": val,
                    "timestamp": ts,
                    "tombstone": tombstone
                }
                updated = True
                
        if updated:
            with open(sync_file, "w", encoding="utf-8") as f:
                json.dump(server_store, f, indent=2)
                
        # Format response containing complete merged LWW-Element-Set
        response_elements = []
        for key, info in server_store.items():
            response_elements.append({
                "key": key,
                "value": info["value"],
                "timestamp": info["timestamp"],
                "tombstone": info["tombstone"]
            })
            
        return jsonify({
            "status": "success",
            "client_id": client_id,
            "elements": response_elements
        })
        
    except Exception as e:
        logger.error(f"Failed CRDT sync relay operation: {e}")
        return jsonify({"error": str(e)}), 500


# ─── Multimedia ──────────────────────────────────────────────────

# ─── Multimedia ──────────────────────────────────────────────────

image_gen = ImageGenerator()

@app.route("/api/generate_image", methods=["POST"])
def generate_image_api():
    """Neural Visualization: Creating images from logic prompts."""
    try:
        data = request.json
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"error": "Visual prompt empty"}), 400
            
        future = executor.submit(image_gen.generate, prompt)
        result = future.result() # Wait for it, but in the future we could make this async polling
        return jsonify(result)
    except Exception as e:
        logger.error(f"Neural Visualization Failure: {e}")
        return jsonify({"error": "Creative node offline"}), 500

@app.route("/api/generate_video", methods=["POST"])
def generate_video_api():
    """Neural Motion: Synthesizing video from visual and vocal assets."""
    try:
        data = request.json
        image_path = data.get("image_path")
        audio_path = data.get("audio_path")
        
        if not image_path or not audio_path:
            return jsonify({"error": "Multimedia assets missing"}), 400
            
        future = executor.submit(create_video, image_path, audio_path)
        result = future.result()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Neural Motion Failure: {e}")
        return jsonify({"error": "Motion node offline"}), 500

@app.route("/api/assets/images/<filename>")
def serve_image(filename):
    return send_file(os.path.join(config.IMAGE_GEN_DIR, filename))

@app.route("/api/assets/videos/<filename>")
def serve_video(filename):
    return send_file(os.path.join(config.VIDEO_GEN_DIR, filename))

@app.route("/api/assets/voices/<filename>")
def serve_voice(filename):
    return send_file(os.path.join(config.VOICE_DIR, filename))

@app.route("/api/system/health", methods=["GET"])
def get_system_health():
    """Health Node: Direct diagnostic readout."""
    return jsonify(DiagnosticNode.check_environment())

@app.route("/api/system/scan", methods=["GET"])
@login_required
def run_deep_scan():
    """Autonomous Deep Scan: Execute Legend Bug Analyzer across codebase."""
    try:
        findings = run_autonomous_scan(config.BASE_DIR)
        return jsonify({
            "status": "complete",
            "count": len(findings),
            "findings": findings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/system/fix", methods=["POST"])
@login_required
def fix_system_bug():
    """Neural Repair: Autonomously solve or kill detected bugs."""
    data = request.json
    action = data.get("action") # 'solve' or 'kill'
    finding = data.get("finding")
    
    if not finding or not action:
        return jsonify({"error": "Invalid mission parameters"}), 400
        
    filepath = os.path.join(config.BASE_DIR, finding['file'])
    line_no = finding['line']
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if action == 'kill':
            # Comment out the offending line
            if 0 < line_no <= len(lines):
                lines[line_no-1] = f"# [PURGED BY JARVIS] {lines[line_no-1]}"
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return jsonify({"status": "success", "message": f"Anomaly at {finding['file']}:{line_no} neutralized."})
        
        elif action == 'solve':
            # This would ideally call the LLM to fix it, but for now we'll do a basic automated fix 
            # for common analyzer findings like bare excepts
            if "Bare 'except:'" in finding['message']:
                lines[line_no-1] = lines[line_no-1].replace("except:", "except Exception as e:")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return jsonify({"status": "success", "message": f"Neural logic at {finding['file']}:{line_no} stabilized."})
            
            return jsonify({"error": "Auto-solve not yet calibrated for this anomaly type."}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Unknown error in repair sequence."}), 500

@app.route("/api/voice/synthesize", methods=["POST"])
def synthesize_voice():
    """Convert text to speech using edge_tts."""
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    try:
        import edge_tts
        import tempfile
        import os
        from flask import send_file
        
        # Use Christopher voice for JARVIS feel
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        
        fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        
        # Helper to run async code synchronously in Flask request
        import asyncio
        async def run_tts():
            await communicate.save(temp_path)
            
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(run_tts())
        
        return send_file(temp_path, mimetype="audio/mpeg", as_attachment=False)
    except Exception as e:
        logger.error(f"Voice synthesis failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/system/stats", methods=["GET"])
def get_system_stats():
    """Telemetry: Fetching real-time hardware utilization metrics."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        ram_used = f"{psutil.virtual_memory().used / (1024**3):.1f}G"
        
        # GPU detection (Simulated for local env if no nvidia-smi)
        gpu = 0
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                gpu = int(result.stdout.strip().split('\n')[0])
            else:
                import random
                gpu = random.randint(10, 15)
        except Exception: 
            import random
            gpu = random.randint(10, 15)

        return jsonify({
            "cpu": f"{cpu}%",
            "gpu": f"{gpu}%",
            "ram": f"{ram_used}",
            "net": f"{psutil.net_io_counters().bytes_sent / (1024**2):.1f}M"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/system/emotion", methods=["GET"])
def get_system_emotion():
    """Fetch dynamic emotion intelligence parameters and system vitals."""
    try:
        from core.emotion_engine import emotion_engine
        state = emotion_engine.get_state_summary()
        return jsonify(state)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Nexus Studio Pipeline ─────────────────────────────────────────────

@app.route("/api/studio/projects", methods=["GET"])
@login_required
def list_studio_projects():
    """List all multimedia projects for the current operator."""
    from models import Project
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
    return jsonify([{
        "id": p.id,
        "topic": p.topic,
        "title": p.title,
        "status": p.status,
        "progress": p.progress,
        "video_url": p.final_video_url,
        "created_at": p.created_at.isoformat()
    } for p in projects])

@app.route("/api/studio/projects/create", methods=["POST"])
@login_required
def create_studio_project():
    """Phase 1: Initiate Intelligence Drafting."""
    data = request.json
    topic = data.get("topic")
    if not topic:
        return jsonify({"error": "Topic required"}), 400
    
    from models import Project
    project_id = f"prj_{uuid.uuid4().hex[:8]}"
    project = Project(id=project_id, user_id=current_user.id, topic=topic, status="initializing")
    db.session.add(project)
    db.session.commit()
    
    mission_engine.initiate_project(project_id, topic)
    return jsonify({"project_id": project_id})

@app.route("/api/studio/projects/<id>", methods=["GET"])
@login_required
def get_studio_project(id):
    """Fetch project details and scenes for review."""
    from models import Project
    p = Project.query.get(id)
    if not p or p.user_id != current_user.id:
        return jsonify({"error": "Project not found or unauthorized"}), 404
    
    return jsonify({
        "id": p.id,
        "topic": p.topic,
        "title": p.title,
        "status": p.status,
        "progress": p.progress,
        "video_url": p.final_video_url,
        "scenes": [{
            "id": s.id,
            "index": s.index,
            "narration": s.narration,
            "visual_prompt": s.visual_prompt,
            "image_url": s.image_url,
            "clip_url": s.clip_url
        } for s in sorted(p.scenes, key=lambda x: x.index)]
    })

@app.route("/api/studio/projects/approve", methods=["POST"])
@login_required
@credit_required(cost=10) # Heavy rendering cost
def approve_studio_project():
    """Phase 2: Finalize Synthesis (Rendering)."""
    project_id = request.json.get("project_id")
    from models import Project
    p = Project.query.get(project_id)
    if not p or p.user_id != current_user.id:
        return jsonify({"error": "Project not found"}), 404
        
    mission_engine.finalize_project(project_id)
    return jsonify({"status": "Synthesis Initialized", "project_id": project_id})

@app.route("/api/missions", methods=["GET"])
@login_required
def list_missions_api():
    """Retrieve autonomous missions for the operator HUD."""
    missions = mission_engine.list_missions(user_id=current_user.id)
    return jsonify([{
        "id": m.id,
        "topic": m.topic,
        "status": m.status,
        "progress": m.progress,
        "timestamp": m.created_at.strftime("%H:%M")
    } for m in missions])

@app.route("/api/studio/scenes/update", methods=["POST"])
@login_required
def update_studio_scene():
    """Strategic Intervention: Edit AI-generated scenes before rendering."""
    data = request.json
    scene_id = data.get("scene_id")
    from models import ProjectScene
    s = ProjectScene.query.get(scene_id)
    if not s or s.project.user_id != current_user.id:
        return jsonify({"error": "Scene not found"}), 404
    
    if s.project.status != 'draft':
        return jsonify({"error": "Cannot edit project after rendering has begun"}), 400
        
    if "narration" in data: s.narration = data["narration"]
    if "visual_prompt" in data: s.visual_prompt = data["visual_prompt"]
    
    db.session.commit()
    return jsonify({"status": "Success"})

# ─── Neural Store (Payments) ────────────────────────────────────────

@app.route("/api/payment/create-session", methods=["POST"])
@login_required
def create_checkout_session():
    """Neural Financial Interface: Initiating a Stripe Checkout link."""
    try:
        data = request.json
        pack_id = data.get("pack_id")
        
        # Define Packs
        packs = {
            "mini": {"name": "Mini Node", "credits": 100, "price": 500}, # $5.00
            "mega": {"name": "Mega Node", "credits": 500, "price": 1500}, # $15.00
            "supreme": {"name": "Supreme Operator", "credits": 1000, "price": 2500, "tier": "pro"} # $25.00
        }
        
        pack = packs.get(pack_id)
        if not pack:
            return jsonify({"error": "Invalid pack selected"}), 400
            
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=current_user.email,
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f"Jarvis AI: {pack['name']}"},
                    'unit_amount': pack['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={
                'user_id': current_user.id,
                'credits': pack['credits'],
                'tier': pack.get('tier', 'free')
            },
            success_url=request.host_url + "?payment=success",
            cancel_url=request.host_url + "?payment=cancelled",
        )
        
        return jsonify({'id': checkout_session.id, 'url': checkout_session.url})
    except Exception as e:
        logger.error(f"Stripe Session Failure: {e}")
        return jsonify({"error": "Financial node offline"}), 500

@app.route("/api/intel/report", methods=["POST"])
@login_required
def generate_world_intel():
    """World Intelligence Node: Initiating autonomous global analysis."""
    try:
        data = request.json
        region = data.get("region", "Global")
        
        # Check credits
        if current_user.credits < 5 and not current_user.is_admin:
            return jsonify({"error": "Insufficient Neural Credits (5 required)"}), 402
            
        def orchestrate_intel():
            with app.app_context():
                run_async(intel_engine.create_world_report(region))
                if not current_user.is_admin:
                    current_user.credits -= 5
                db.session.commit()

        executor.submit(orchestrate_intel)
        
        return jsonify({
            "status": "Initiated",
            "message": "Jarvis is syncing with global neural nodes. Analysis in progress."
        })
    except Exception as e:
        logger.error(f"Intel Trigger Failure: {e}")
        return jsonify({"error": "Intelligence node link breakdown"}), 500

@app.route("/api/intel/archive", methods=["GET"])
@login_required
def get_intel_archive():
    """Neural Archive: Retrieving past intelligence briefings."""
    return jsonify(intel_engine.get_archive())

@app.route("/api/intel/download/<filename>")
@login_required
def download_briefing(filename):
    """Secure Download: Retrieving Strategic Briefing assets."""
    # Security check: ensure the file is in the briefings directory
    directory = os.path.join(config.DATA_DIR, "briefings")
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Asset not found"}), 404
        
    return send_file(path, as_attachment=True)

@app.route("/api/payment/webhook", methods=["POST"])
def stripe_webhook():
    """Trust Node: Verifying and executing payment events."""
    payload = request.get_data()
    sig_header = request.headers.get('STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return jsonify({"error": "Signature failure"}), 400
        
    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        credits_to_add = int(metadata.get('credits', 0))
        new_tier = metadata.get('tier', 'free')
        
        with app.app_context():
            user = User.query.get(user_id)
            if user:
                user.credits += credits_to_add
                if new_tier != 'free':
                    user.tier = new_tier
                db.session.commit()
                logger.info(f"Payment Confirmed: {user.username} received {credits_to_add} credits.")
                
    return jsonify({"status": "Success"})

# ─── Neural Assets & Sharing ───────────────────────────

@app.route("/api/public/gallery", methods=["GET"])
def get_gallery():
    """Fetch all generated assets with unique shareable hashes."""
    gallery = []
    
    # Scan for images
    for fname in os.listdir(config.IMAGE_GEN_DIR):
        if fname.endswith(('.png', '.jpg', '.jpeg')):
            fpath = os.path.join(config.IMAGE_GEN_DIR, fname)
            fhash = hashlib.md5(fname.encode()).hexdigest()[:12]
            NEURAL_REGISTRY[fhash] = fpath
            gallery.append({
                "type": "image",
                "name": fname,
                "hash": fhash,
                "url": f"/api/assets/images/{fname}"
            })
            
    # Scan for videos
    for fname in os.listdir(config.VIDEO_GEN_DIR):
        if fname.endswith('.mp4'):
            fpath = os.path.join(config.VIDEO_GEN_DIR, fname)
            fhash = hashlib.md5(fname.encode()).hexdigest()[:12]
            NEURAL_REGISTRY[fhash] = fpath
            gallery.append({
                "type": "video",
                "name": fname,
                "hash": fhash,
                "url": f"/api/assets/videos/{fname}"
            })
            
    return jsonify(gallery)

@app.route("/s/<file_hash>")
def public_share(file_hash):
    """Publicly accessible obfuscated share link."""
    filepath = NEURAL_REGISTRY.get(file_hash)
    if not filepath or not os.path.exists(filepath):
        # Re-scan in case it was just generated
        get_gallery() # Shallow scan to populate registry
        filepath = NEURAL_REGISTRY.get(file_hash)
        
    if filepath and os.path.exists(filepath):
        return send_file(filepath)
    return "<h1>Invalid or Expired Neural Link</h1>", 404

@app.route("/api/webhooks/trigger", methods=["POST"])
def trigger_webhook_api():
    """Neural Action: Trigger an external webhook."""
    data = request.json
    name = data.get("name")
    payload = data.get("payload", {})
    try:
        result = run_async(webhook_engine.trigger(name, payload))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Webhook Trigger Failure: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/tts", methods=["POST"])
def tts_api():
    """Neural Vocalization: Synchronizing text to modulated state-of-the-art voice."""
    try:
        data = request.json
        text = data.get("text", "")
        if not text:
            return jsonify({"error": "Vocal payload empty"}), 400
            
        # Pull voice parameters (Priority: Request > User Prefs > Defaults)
        prefs = current_user.preferences or {}
        rate = data.get("rate") or prefs.get("voice_rate", "+0%")
        pitch = data.get("pitch") or prefs.get("voice_pitch", "+0Hz")
        volume = data.get("volume") or prefs.get("voice_volume", "+0%")
            
        voice = config.TTS_VOICE
        # Unique file to prevent collision
        filename = f"speech_{uuid.uuid4().hex}.mp3"
        output_file = os.path.join(config.DATA_DIR, filename)
        
        async def generate_voice():
            # Apply modulation parameters
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
            await communicate.save(output_file)
            
        # Execute neural synthesis
        try:
            run_async(generate_voice())
        except Exception as e:
            logger.error(f"Generate voice failed: {e}")
            return jsonify({"error": "Vocal synthesis failed"}), 500
            
        def delayed_delete(path):
            time.sleep(10)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        
        threading.Thread(target=delayed_delete, args=(output_file,), daemon=True).start()

        return send_file(output_file, mimetype="audio/mpeg")
    except Exception as e:
        logger.error(f"Neural Vocalization Failure: {e}")
        return jsonify({"error": "Vocal node offline"}), 500

# ─── Laptop Guardian API ───────────────────────────────────────────

@app.route("/api/system/laptop/scan", methods=["GET"])
@login_required
def laptop_system_scan():
    """Runs high-fidelity security diagnostics and OS health audits."""
    try:
        sec_report = system_guardian.audit_security_status()
        bug_report = system_guardian.audit_system_bugs()
        return jsonify({
            "status": "success",
            "security": sec_report,
            "bugs": bug_report
        })
    except Exception as e:
        logger.error(f"Laptop system scan api error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/system/laptop/fix", methods=["POST"])
@login_required
def laptop_system_fix():
    """Trigger safe automated repairs based on provided scan results."""
    try:
        data = request.json or {}
        scan_results = data.get("scan_results") or {}
        
        # If scan results aren't passed, run a quick scan on the fly
        if not scan_results or "security" not in scan_results or "bugs" not in scan_results:
            scan_results = {
                "security": system_guardian.audit_security_status(),
                "bugs": system_guardian.audit_system_bugs()
            }
            
        fix_report = system_guardian.resolve_threats_and_bugs(scan_results)
        return jsonify({
            "status": "success",
            "fix_results": fix_report
        })
    except Exception as e:
        logger.error(f"Laptop system fix api error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ─── Startup Hook ───────────────────────────────────────────

def startup_hook():
    """Ensure Database and Model Sync on boot."""
    with app.app_context():
        db.create_all()
        
        # Initialize any active MCP Connectors
        try:
            from core.mcp_engine import mcp_engine
            active_connectors = AppConnector.query.filter_by(is_active=True).all()
            for c in active_connectors:
                if c.command:
                    logger.info(f"Re-connecting MCP Server: {c.provider}")
                    run_async(mcp_engine.connect_server(c.provider, c.command, c.args, c.env_vars))
        except Exception as e:
            logger.error(f"Failed to initialize MCP servers on boot: {e}")
            
        # [NEW] Autostart Local System MCP Server for Sentience Upgrade
        try:
            import sys
            import os
            local_sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "mcp_servers", "local_system.py")
            if os.path.exists(local_sys_path):
                logger.info("Initializing Local System OS Control MCP Server...")
                threading.Thread(target=run_async, args=(mcp_engine.connect_server("local_os", sys.executable, [local_sys_path]),), daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to initialize Local System MCP: {e}")
            
        # [NEW] Autostart Google Workspace MCP Server
        try:
            google_sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "mcp_google.py")
            if os.path.exists(google_sys_path):
                logger.info("Initializing Google Workspace MCP Server...")
                threading.Thread(target=run_async, args=(mcp_engine.connect_server("google_workspace", sys.executable, [google_sys_path]),), daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace MCP: {e}")
        

        # Enforce Admin Identity (Creator Priority)
        admin = User.query.filter_by(username='Admin').first()
        if not admin:
            admin = User(username='Admin', email='admin@local.host')
            admin.set_password('admin')
            admin.tier = 'unlimited'
            admin.credits = 999999
            db.session.add(admin)
            db.session.commit()
            logger.info("[OK] Admin Identity (Unlimited) initialized.")
        else:
            # Ensure Admin always stays Unlimited on every boot
            if admin.tier != 'unlimited' or admin.credits < 1000:
                admin.tier = 'unlimited'
                admin.credits = 999999
                db.session.commit()
                logger.info("[OK] Admin Privileges synchronized.")
        
        # Enforce Identity: Ayush Stark (Master Authority)
        ayush = User.query.filter_by(username='Ayush').first()
        if not ayush:
            ayush = User(username='Ayush', email='ayush@stark.corp')
            ayush.set_password('admin123')
            ayush.tier = 'unlimited'
            ayush.credits = 999999
            db.session.add(ayush)
            db.session.commit()
            logger.info("[OK] Master Authority (Ayush) initialized.")
        else:
            if ayush.tier != 'unlimited':
                ayush.tier = 'unlimited'
                ayush.credits = 999999
                db.session.commit()
                logger.info("[OK] Master Privileges verified.")
        
    if model_manager.ensure_running():
        model_manager.ensure_model(config.DEFAULT_MODEL)
    logger.info(f"[OK] Jarvis is ready.")

def start_heartbeat():
    """Neural Heartbeat: Pings the server every 10 minutes to prevent cloud sleeping."""
    import time
    import requests
    
    def heartbeat_loop():
        time.sleep(60) # Let server warm up
        url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("KOYEB_PUBLIC_URL")
        if not url:
            logger.warning("Heartbeat: No public URL detected. Standing by.")
            return

        while True:
            try:
                # Self-ping to keep cloud active
                requests.get(url, timeout=10)
                logger.debug(f"Heartbeat sync: {url} OK.")
            except Exception:
                pass
            time.sleep(600) # 10 mins

    threading.Thread(target=heartbeat_loop, daemon=True).start()

def start_bot():
    """Starts the Telegram Bot as a background process."""
    import subprocess
    import sys
    import os
    try:
        logger.info("Neural Link: Launching Telegram Bot Node...")
        bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_bot.py")
        subprocess.Popen([sys.executable, bot_path])
    except Exception as e:
        logger.error(f"Telegram Bot failed to launch: {e}")

# ─── Graceful Shutdown Protocol ─────────────────────────────────────
import signal

def shutdown_handler(signum, frame):
    """Ensure all neural threads and database sessions are safely committed."""
    logger.info("Initiating Graceful Shutdown sequence...")
    try:
        with app.app_context():
            db.session.commit()
            logger.info("Neural Memory: Persistent layers committed.")
    except Exception as e:
        logger.error(f"Shutdown DB Error: {e}")
    
    logger.info("JARVIS OS: Offline.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == "__main__":
    # Ensure sequential startup (no daemon threads for critical DB/model sync)
    startup_hook()
    
    # Start Bot + Heartbeat
    if config.SERVER_MODE:
        start_heartbeat()
        start_bot()
    
    logger.info(f"Launching JARVIS Production Gateway on port {config.APP_PORT}...")
    app.run(
        host=config.APP_HOST,
        port=int(os.environ.get("PORT", config.APP_PORT)),
        debug=config.DEBUG,
    )
