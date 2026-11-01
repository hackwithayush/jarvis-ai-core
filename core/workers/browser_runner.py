"""
JARVIS Autonomous Web Agent Runner (Browser Use Engine)
Operates within .venv_browser to provide deterministic, visual, and multi-step web autonomy.
"""
import asyncio
import json
import os
import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("jarvis.browser_runner")

def build_llm(provider: str = None, model: str = None):
    from browser_use.llm import ChatGoogle, ChatGroq, ChatOpenAI, ChatOllama
    
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    provider = (provider or "").lower().strip()
    
    # 1. Google Gemini (Default choice: fast, multimodal, native vision)
    if provider == "google" or (not provider and gemini_key):
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not configured in environment.")
        model_name = model or "gemini-2.0-flash"
        logger.info(f"Initialized ChatGoogle with model: {model_name}")
        return ChatGoogle(model=model_name, api_key=gemini_key)
        
    # 2. Groq (High-speed inference)
    if provider == "groq" or (not provider and groq_key):
        if not groq_key:
            raise ValueError("GROQ_API_KEY is not configured in environment.")
        model_name = model or "llama-3.3-70b-versatile"
        logger.info(f"Initialized ChatGroq with model: {model_name}")
        return ChatGroq(model=model_name, api_key=groq_key)
        
    # 3. OpenAI
    if provider == "openai" or (not provider and openai_key):
        if not openai_key:
            raise ValueError("OPENAI_API_KEY is not configured in environment.")
        model_name = model or "gpt-4o"
        logger.info(f"Initialized ChatOpenAI with model: {model_name}")
        return ChatOpenAI(model=model_name, api_key=openai_key)
        
    # 4. Local Ollama fallback
    logger.info("Falling back to local Ollama")
    return ChatOllama(model=model or "llama3")

async def run_autonomous_browser(task: str, headless: bool = False, provider: str = None, model: str = None, max_steps: int = 15):
    from browser_use import Agent, BrowserProfile

    logger.info(f"Launching JARVIS Autonomous Browser Agent. Task: '{task}' | Headless: {headless}")
    
    llm = build_llm(provider=provider, model=model)
    
    # Configure BrowserProfile
    profile = BrowserProfile(
        headless=headless,
        disable_security=True,
    )
    
    # Initialize Agent
    agent = Agent(
        task=task,
        llm=llm,
        browser_profile=profile,
        use_vision=True,
        max_failures=3,
        max_actions_per_step=3
    )
    
    history = await agent.run(max_steps=max_steps)
    
    final_result = history.final_result() if hasattr(history, "final_result") else str(history)
    urls_visited = history.urls() if hasattr(history, "urls") else []
    errors = history.errors() if hasattr(history, "errors") else []
    
    result_payload = {
        "status": "success",
        "task": task,
        "final_result": final_result,
        "urls_visited": urls_visited,
        "errors": errors,
        "total_steps": len(history.history) if hasattr(history, "history") else 0
    }
    
    # Print delimited JSON result for parent process parsing
    print("\n__JARVIS_BROWSER_RESULT_START__")
    print(json.dumps(result_payload, indent=2))
    print("__JARVIS_BROWSER_RESULT_END__\n")
    
    return result_payload

def main():
    parser = argparse.ArgumentParser(description="JARVIS Autonomous Browser Runner")
    parser.add_argument("--task", type=str, required=True, help="Autonomous web browsing directive")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    parser.add_argument("--provider", type=str, default=None, help="LLM Provider: google, groq, openai, ollama")
    parser.add_argument("--model", type=str, default=None, help="LLM Model name")
    parser.add_argument("--max-steps", type=int, default=15, help="Maximum agent actions")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_autonomous_browser(
            task=args.task,
            headless=args.headless,
            provider=args.provider,
            model=args.model,
            max_steps=args.max_steps
        ))
    except Exception as e:
        logger.exception(f"Autonomous Browser execution failed: {e}")
        error_payload = {
            "status": "error",
            "task": args.task,
            "error": str(e)
        }
        print("\n__JARVIS_BROWSER_RESULT_START__")
        print(json.dumps(error_payload, indent=2))
        print("__JARVIS_BROWSER_RESULT_END__\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
