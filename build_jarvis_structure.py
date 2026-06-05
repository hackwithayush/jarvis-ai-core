import os
from pathlib import Path

base_dir = r"c:\Users\AYUSH CHAUDHARY\OneDrive\Desktop\assistant.py\jarvis-ai"

directories = [
    "CORE",
    "MODELS/LOCAL/qwen2.5-coder-7b",
    "MODELS/LOCAL/deepseek-r1-7b",
    "MODELS/LOCAL/llama3.1-8b",
    "MODELS/LOCAL/embeddings/all-MiniLM-L6-v2",
    "MODELS/CLOUD",
    "MODELS/MODEL_ROUTING",
    "MEMORY/chromadb",
    "MEMORY/faiss",
    "MEMORY/vector_store",
    "MEMORY/conversation_memory",
    "MEMORY/long_term_memory",
    "MEMORY/embeddings_cache",
    "AGENTS/coding_agent",
    "AGENTS/research_agent",
    "AGENTS/automation_agent",
    "AGENTS/gaming_agent",
    "AGENTS/voice_agent",
    "AGENTS/web_agent",
    "AGENTS/planner_agent",
    "VOICE/whisper",
    "VOICE/tts",
    "VOICE/wake_word",
    "VOICE/microphone",
    "AUTOMATION",
    "TOOLS/browser_control",
    "TOOLS/file_system",
    "TOOLS/terminal_control",
    "TOOLS/telegram_bot",
    "TOOLS/discord_bot",
    "TOOLS/obs_control",
    "TOOLS/vscode_control",
    "TOOLS/web_search",
    "API/routes",
    "API/middleware",
    "API/auth",
    "UI/desktop_dashboard",
    "UI/web_dashboard",
    "UI/futuristic_ui",
    "UI/system_monitor",
    "UI/realtime_console",
    "VISION/screenshot_analysis",
    "VISION/image_processing",
    "VISION/ocr",
    "VISION/object_detection",
    "SECURITY/encryption",
    "SECURITY/permissions",
    "SECURITY/sandbox_execution",
    "DATABASE",
    "MONITORING/performance_logs",
    "DEV/jarvislang",
    "DEV/testing",
    "DEV/debugging",
    "DEV/experimental",
    "INSTALLER/docker"
]

files = {
    "CORE/jarvis_brain.py": '""" Jarvis Brain """\n',
    "CORE/neural_router.py": '""" Neural Router """\n',
    "CORE/task_classifier.py": '""" Task Classifier """\n',
    "CORE/memory_manager.py": '""" Memory Manager """\n',
    "CORE/context_engine.py": '""" Context Engine """\n',
    "CORE/config.py": '""" Core Config """\n',
    "CORE/startup.py": '""" Startup Sequence """\n',
    "MODELS/CLOUD/groq_client.py": '""" Groq Client """\n',
    "MODELS/CLOUD/llama70b.py": '""" Llama 70B Interface """\n',
    "MODELS/CLOUD/vision_model.py": '""" Vision Model Interface """\n',
    "MODELS/CLOUD/fallback_router.py": '""" Fallback Router """\n',
    "MODELS/MODEL_ROUTING/coding_router.py": '""" Coding Router """\n',
    "MODELS/MODEL_ROUTING/reasoning_router.py": '""" Reasoning Router """\n',
    "MODELS/MODEL_ROUTING/chat_router.py": '""" Chat Router """\n',
    "MODELS/MODEL_ROUTING/vision_router.py": '""" Vision Router """\n',
    "VOICE/voice_pipeline.py": '""" Voice Pipeline """\n',
    "AUTOMATION/task_scheduler.py": '""" Task Scheduler """\n',
    "AUTOMATION/workflow_engine.py": '""" Workflow Engine """\n',
    "AUTOMATION/smart_actions.py": '""" Smart Actions """\n',
    "AUTOMATION/command_executor.py": '""" Command Executor """\n',
    "AUTOMATION/process_manager.py": '""" Process Manager """\n',
    "API/fastapi_server.py": '""" FastAPI Server """\n',
    "API/websocket_server.py": '""" Websocket Server """\n',
    "SECURITY/token_manager.py": '""" Token Manager """\n',
    "DATABASE/users.db": '',
    "DATABASE/memory.db": '',
    "DATABASE/analytics.db": '',
    "DATABASE/logs.db": '',
    "MONITORING/gpu_monitor.py": '""" GPU Monitor """\n',
    "MONITORING/ram_monitor.py": '""" RAM Monitor """\n',
    "MONITORING/model_usage.py": '""" Model Usage """\n',
    "MONITORING/optimizer.py": '""" Optimizer """\n',
    "INSTALLER/setup.bat": '@echo off\necho Installing JARVIS-AI...\n',
    "INSTALLER/install_models.py": '""" Install Models Script """\n',
    "INSTALLER/requirements.txt": '# Requirements\n',
    "INSTALLER/launcher.exe": '',
    ".env": '# Environment Variables\n',
    "README.md": '# JARVIS AI\n\nAdvanced Autonomous AI Assistant.\n',
    "main.py": '""" Main Entry Point for JARVIS """\n'
}

for d in directories:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

for f_path, content in files.items():
    full_path = os.path.join(base_dir, f_path)
    if not os.path.exists(full_path):
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

print("JARVIS-AI structure created successfully!")
