"""
JARVIS Autonomous Browser Engine (Powered by Browser Use)
Integrates multi-step, visual web browsing and DOM automation into the StarkOS core.
"""
import os
import sys
import json
import logging
import subprocess
import asyncio
from typing import Dict, Any, Optional

import config

logger = logging.getLogger("jarvis.browser_engine")

class BrowserEngine:
    """Central gateway to the isolated Browser-Use autonomous web subsystem."""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.venv_python = os.path.join(self.base_dir, ".venv_browser", "Scripts", "python.exe")
        self.runner_script = os.path.join(self.base_dir, "core", "workers", "browser_runner.py")
        
        # Verify runner readiness
        self.is_available = os.path.exists(self.venv_python) and os.path.exists(self.runner_script)
        if self.is_available:
            logger.info("BrowserEngine: Browser-Use subsystem online and ready.")
        else:
            logger.warning(f"BrowserEngine: Subsystem incomplete (venv: {os.path.exists(self.venv_python)}, runner: {os.path.exists(self.runner_script)})")

    def _prepare_env(self) -> Dict[str, str]:
        """Inject active API keys into the worker environment."""
        env = os.environ.copy()
        
        if hasattr(config, "GEMINI_API_KEY") and config.GEMINI_API_KEY:
            env["GEMINI_API_KEY"] = config.GEMINI_API_KEY
            env["GOOGLE_API_KEY"] = config.GEMINI_API_KEY
        if hasattr(config, "GROQ_API_KEY") and config.GROQ_API_KEY:
            env["GROQ_API_KEY"] = config.GROQ_API_KEY
        if hasattr(config, "OPENAI_API_KEY") and config.OPENAI_API_KEY:
            env["OPENAI_API_KEY"] = config.OPENAI_API_KEY
            
        return env

    def execute_task(
        self,
        task: str,
        headless: bool = False,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_steps: int = 15,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute an autonomous web browsing task synchronously.
        """
        if not self.is_available:
            return {
                "status": "error",
                "error": "Browser-Use subsystem environment is not configured or missing."
            }

        cmd = [
            self.venv_python,
            self.runner_script,
            "--task", task,
            "--max-steps", str(max_steps)
        ]
        
        if headless:
            cmd.append("--headless")
        if provider:
            cmd.extend(["--provider", provider])
        if model:
            cmd.extend(["--model", model])
        else:
            # Default to gemini-2.5-flash for maximum reliability & speed
            cmd.extend(["--model", "gemini-2.5-flash"])

        logger.info(f"BrowserEngine: Spawning worker for task: '{task}'")
        
        try:
            proc = subprocess.run(
                cmd,
                env=self._prepare_env(),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = proc.stdout
            
            # Extract JSON block between delimiters
            start_marker = "__JARVIS_BROWSER_RESULT_START__"
            end_marker = "__JARVIS_BROWSER_RESULT_END__"
            
            if start_marker in output and end_marker in output:
                json_str = output.split(start_marker)[1].split(end_marker)[0].strip()
                try:
                    result = json.loads(json_str)
                    return result
                except Exception as e:
                    logger.error(f"BrowserEngine: Failed to parse JSON result: {e}")
            
            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or output.strip()
                logger.error(f"BrowserEngine: Worker failed with code {proc.returncode}: {err_msg}")
                return {
                    "status": "error",
                    "error": f"Browser process error: {err_msg[:300]}"
                }
                
            return {
                "status": "success",
                "task": task,
                "final_result": output.strip()
            }

        except subprocess.TimeoutExpired:
            logger.error(f"BrowserEngine: Task timed out after {timeout} seconds.")
            return {
                "status": "error",
                "error": f"Browser task timed out after {timeout}s."
            }
        except Exception as e:
            logger.exception(f"BrowserEngine: Execution error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def execute_task_async(
        self,
        task: str,
        headless: bool = False,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_steps: int = 15,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """Asynchronous execution wrapper for asyncio loops."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.execute_task,
            task,
            headless,
            provider,
            model,
            max_steps,
            timeout
        )

# Global Singleton
browser_engine = BrowserEngine()
