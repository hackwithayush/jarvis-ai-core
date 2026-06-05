"""
Agent Pipeline — Multi-Agent Intelligence System
Planner → Executor → Critic architecture for Claude-style reasoning.
Uses local Ollama models for planning and critique — no external API needed.
"""
import json
import logging
import re
import os
from datetime import datetime, timezone
from typing import Optional, Generator

import config
from core.utils import safe_json_parse, retry_sync

logger = logging.getLogger(__name__)


# ─── Tool Definitions (for the Planner) ─────────────────────────
TOOL_DEFINITIONS = """
Available tools you can use:
1. "deep_research" — High-level autonomous research loop. Combines multiple searches and article scraping. Use for complex questions.
2. "manage_missions" — Create, list, or complete user tasks/missions.
3. "web_search" — Search the web for specific real-time information.
4. "news_feed" — Get latest news from RSS feeds on specific topics.
5. "generate_image" — Create a NEW image from a text description. Use when user says "generate/draw/create image".
6. "edit_image" — Edit an existing image. Use when the user provides an image and asks to "edit/change/modify" it.
7. "generate_video" — Create an AI video from a text prompt. Use when user says "create/make video".
8. "run_code" — Execute Python code.
9. "read_file" — Read contents of a file.
10. "os_control" — Manage Windows system (health, launch apps, list processes).
11. "file_mastery" — Organize folders, search for files, or summarize document content. Use for "clean my desktop", "find file", or "whats in this file".
12. "system_guardian" — Audit and secure the user's host laptop system. Find security threats (viruses/persistence items), analyze Windows Event log bugs, resource hogs, temp bloat, and perform automated fixes (clean temp directories, flush DNS, terminate resource hogs, trigger Windows Defender malware scan). Use for "scan my laptop", "find viruses", "security audit", "fix system bugs", "solve system threats", "malware scan".
13. "none" — No tool needed.
"""

# ─── Intent Patterns ────────────────────────────────────────────
INTENT_PATTERNS = {
    "web_search": [
        "search", "look up", "find", "google", "latest", "current",
        "who is", "what is", "where is", "when did", "how to",
        "trending", "tell me about", "explain",
    ],
    "news_feed": [
        "news", "headlines", "breaking", "updates",
        "what happened", "what's happening",
    ],
    "web_scrape": [
        "http://", "https://", "www.",
        "scrape", "extract from",
    ],
    "generate_image": [
        "generate image", "create image", "draw", "make an image", "create a picture",
        "generate a photo", "draw a", "anime", "realistic", "cyberpunk", "3d render",
        "logo", "sketch", "car image", "portrait", "suit", "character", "design",
        "logo",
    ],
    "edit_image": [
        "edit image", "change image", "modify image", "edit this", "style this",
        "make it anime", "make it cyberpunk", "transform image",
    ],
    "generate_video": [
        "generate video", "create video", "make video", "ai video", "video of",
    ],
    "run_code": [
        "run this", "execute", "test this code",
        "run python", "execute python",
    ],
    "read_file": [
        "read file", "open file", "show file", "cat ",
    ],
    "write_file": [
        "save to file", "write to file", "save this",
        "create file", "store this",
    ],
    "calculate": [
        "calculate", "compute", "math", "what is the result of",
        "solve", "evaluate",
    ],
    "datetime": [
        "what time", "current time", "what date", "today's date",
        "what day",
    ],
    "os_control": [
        "system health", "cpu", "ram", "status", "what's running", 
        "open ", "launch ", "start ", "apps running", "system audit"
    ],
    "file_mastery": [
        "clean my", "organize", "sort my", "find file", "search for file",
        "summarize this", "whats in", "read documented", "lookup file"
    ],
    "system_guardian": [
        "scan my laptop", "system guardian", "find viruses", "security audit",
        "fix system bugs", "solve system threats", "malware scan", "clean temp files",
        "laptop scan", "laptop audit", "defender scan", "system scan", "scan laptop"
    ]
}

# Greetings that should skip the agent pipeline entirely
GREETING_PATTERNS = [
    "hi", "hii", "hyy", "hey", "hello", "hola", "sup",
    "good morning", "good evening", "good night",
    "bye", "goodbye", "thanks", "thank you", "ok", "okay",
]


class AgentPipeline:
    """
    Multi-agent pipeline: Planner → Executor → Critic.
    Routes user messages through intelligent tool selection and response refinement.
    """

    def __init__(self, model_manager, knowledge_manager, web_search_engine):
        self.model = model_manager
        self.knowledge = knowledge_manager
        self.web_search = web_search_engine
        self.max_steps = getattr(config, "AGENT_MAX_STEPS", 3)
        self.critic_enabled = getattr(config, "AGENT_CRITIC_ENABLED", False)

        # Lazy import tools
        self._tools = None

    @property
    def tools(self):
        """Lazy-load tool engine."""
        if self._tools is None:
            from core.tools import ToolEngine
            self._tools = ToolEngine()
        return self._tools

    # ─── 1. PLANNER ─────────────────────────────────────────────────

    @retry_sync(retries=2, delay=1.0)
    def plan(self, message: str, context: list = None) -> dict:
        """
        Analyze user intent and decide which tool to use via LLM-based reasoning.
        Returns: {"tool": str, "query": str, "topic": str, "reason": str}
        """
        msg = message.lower().strip()

        # Phase 0: Quick Greeting Filter (Efficiency)
        if self._is_greeting(msg):
            return {"tool": "none", "query": message, "topic": "", "reason": "greeting detected"}

        try:
            # Phase 0.5: Intent Refinement (Sanitize input for the planner)
            refined_message = self._refine_intent(message)
            logger.info(f"Agent Node: Intent refined for planner.")

            # Phase 1: Neural Planning
            planner_prompt = (
                "You are the Neural Planner for JARVIS v15.0.\n"
                "Your job is to decide if a user request needs an external tool or a direct response.\n\n"
                f"{TOOL_DEFINITIONS}\n"
                "RULES:\n"
                "1. If latest info, news, or current events are needed -> web_search or news_feed.\n"
                "2. If math/logic calculation needed -> calculate.\n"
                "3. If URL is given -> web_scrape.\n"
                "4. If code execution is needed -> run_code.\n"
                "5. Return ONLY a valid JSON object.\n\n"
                f"User Message: {refined_message}\n"
                "JSON Output:"
            )

            # Use a fast model for planning
            response = self.model.generate(
                messages=[{"role": "user", "content": planner_prompt}],
                system_prompt="You are a precise tool router. Output ONLY valid JSON. Must be a JSON object with 'tool', 'query', 'topic', and 'reason' keys.",
                model=config.ROUTING_CONFIG.get("fast", "phi3:mini"),
                response_format={"type": "json_object"}
            )

            # JSON Parsing directly (guaranteed by structured output)
            try:
                import json
                data = json.loads(response)
            except Exception as e:
                logger.error(f"Structured JSON parsing failed: {e}")
                data = {"tool": "none"}
            
            # Midjourney-level Smart Detection override:
            # If any visual keywords are present, force generate_image
            visual_keywords = ["anime", "render", "8k", "4k", "realistic", "wallpaper", "portrait", "design", "logo", "img", "photo", "picture", "dinosaur", "art"]
            if any(kw in message.lower() for kw in visual_keywords) and data.get("tool") == "none":
                data["tool"] = "generate_image"
                data["topic"] = message

            # Register telemetry trace for planner decision
            try:
                from core.telemetry import telemetry_manager
                telemetry_manager.add_trace(f"Planner routed user query to '{data.get('tool')}' (Reason: {data.get('reason')})")
            except Exception:
                pass

            return {
                "tool": data.get("tool", "none"),
                "query": data.get("query", message),
                "topic": data.get("topic", ""),
                "reason": data.get("reason", "neural reasoning")
            }

        except Exception as e:
            logger.error(f"Neural Planner critical failure: {e}")
            try:
                from core.telemetry import telemetry_manager
                telemetry_manager.add_trace(f"Planner failed: {e}")
            except Exception:
                pass
            return {"tool": "none", "query": message, "topic": "", "reason": f"error: {e}"}

    # ─── 2. EXECUTOR ────────────────────────────────────────────────

    def execute(self, plan: dict, message: str) -> str:
        """
        Execute the planned tool and return raw results.
        """
        tool = plan["tool"]
        query = plan.get("query", message)
        topic = plan.get("topic", "")

        logger.info(f"Agent executing: tool={tool}, topic={topic}")

        import time
        from core.telemetry import telemetry_manager
        start_t = time.time()

        try:
            res = ""
            if tool == "deep_research":
                res = self._exec_deep_research(query)

            elif tool == "manage_missions":
                res = self._exec_manage_missions(message)

            elif tool == "web_search":
                res = self._exec_web_search(topic or query)

            elif tool == "multi_search":
                res = self._exec_multi_search(query, topic)

            elif tool == "web_scrape":
                res = self._exec_scrape(query)

            elif tool == "run_code":
                code = self._extract_code(message)
                if code:
                    # Self-Repair Loop (Upgrade 3)
                    max_attempts = 3
                    attempt = 0
                    while attempt < max_attempts:
                        res = self.tools.execute_python_code(code)
                        if "Error:" not in res and "Exception:" not in res and "Traceback" not in res and "SyntaxError" not in res:
                            break # Success
                        attempt += 1
                        if attempt >= max_attempts:
                            break
                        logger.info(f"Self-Repair Loop Attempt {attempt}/{max_attempts} for run_code.")
                        repair_prompt = f"The following Python code failed to execute:\n\n```python\n{code}\n```\n\nError Output:\n{res}\n\nFix the code and return ONLY the corrected Python code in a code block."
                        repair_response = self.model.generate(
                            messages=[{"role": "user", "content": repair_prompt}],
                            system_prompt="You are an expert Python debugger. Output ONLY the fixed Python code.",
                            model=config.ROUTING_CONFIG.get("coding", "llama-3.3-70b-versatile")
                        )
                        fixed_code = self._extract_code(repair_response)
                        if fixed_code:
                            code = fixed_code
                        else:
                            break

            elif tool == "read_file":
                filepath = self._extract_filepath(message)
                if filepath:
                    res = self.tools.read_file(filepath)

            elif tool == "write_file":
                filepath, content = self._extract_file_write(message)
                if filepath and content:
                    res = self.tools.write_file(filepath, content)

            elif tool == "calculate":
                expr = self._extract_math(message)
                if expr:
                    res = self.tools.calculate(expr)

            elif tool == "datetime":
                res = self.tools.get_datetime()

            elif tool == "generate_image":
                res = self._exec_gen_image(query)

            elif tool == "edit_image":
                # Note: For edit, the file path must be handled by the bot or provided in query
                res = self._exec_edit_image(query)

            elif tool == "generate_video":
                res = self._exec_gen_video(query)

            elif tool == "os_control":
                res = self._exec_os_control(message)

            elif tool == "file_mastery":
                res = self._exec_file_mastery(message)

            elif tool == "system_guardian":
                res = self._exec_system_guardian(message)

            duration_ms = (time.time() - start_t) * 1000.0
            telemetry_manager.add_tool_log(tool, query, "success", duration_ms)
            return res

        except Exception as e:
            logger.error(f"Agent execution error ({tool}): {e}")
            duration_ms = (time.time() - start_t) * 1000.0
            telemetry_manager.add_tool_log(tool, query, "error", duration_ms)
            telemetry_manager.add_trace(f"Tool '{tool}' execution failed: {e}")
            return ""

    # ─── 3. CRITIC (Optional Refinement) ────────────────────────────

    @retry_sync(retries=2, delay=1.0)
    def critique(self, tool_output: str, original_message: str) -> str:
        """
        Use the LLM to refine raw tool output into a clean response.
        Only runs if critic is enabled and there's actual tool output.
        """
        if not self.critic_enabled or not tool_output:
            return tool_output

        try:
            critic_prompt = (
                "You are the JARVIS Intelligence Ranker.\n"
                "I have gathered data from multiple sources. Your task is to select the BEST, most relevant, "
                "and most up-to-date information to answer the user's query.\n\n"
                f"User Query: {original_message}\n"
                f"Raw Multi-Source Data:\n{tool_output[:3000]}\n\n"
                "GOAL: Filter out noise, rank the most important facts high, and write a clean, natural response:"
            )

            # Use Prime Node for high-quality ranking if available
            model = config.ROUTING_CONFIG.get("prime", "gpt-4o")
            response = self.model.generate(
                messages=[{"role": "user", "content": critic_prompt}],
                system_prompt="You are a senior intelligence analyst. Select and rank the best info.",
                model=model
            )
            return response if response else tool_output

        except Exception as e:
            logger.error(f"Critic error: {e}")
            return tool_output

    @retry_sync(retries=2, delay=1.0)
    def refine_response(self, response: str, original_message: str) -> str:
        """
        Final pass: Optimize the LLM's response for clarity, brevity, and tone.
        Indistinguishable from ChatGPT quality.
        """
        if not self.critic_enabled or not response:
            return response

        try:
            refine_prompt = (
                "You are the JARVIS Quality Critic.\n"
                "Review the draft response below and improve it.\n"
                "GOALS: Clearer, shorter, more useful, and natural tone.\n"
                "ANTI-ROBOT: Remove any 'I am an AI' or knowledge cutoff mentions.\n\n"
                f"User: {original_message}\n"
                f"Draft: {response}\n\n"
                "Final Refined Response:"
            )

            # Use a fast but capable model logic
            refined = self.model.generate(
                messages=[{"role": "user", "content": refine_prompt}],
                system_prompt="You are a professional editor. Output ONLY the refined response.",
                model=config.ROUTING_CONFIG.get("prime", "gpt-4o") # Use prime for final polish
            )
            return refined if refined else response

        except Exception as e:
            logger.error(f"Response refinement error: {e}")
            return response

    # ─── 4. AUTONOMOUS LOOP ─────────────────────────────────────────

    def run(self, message: str, context: list = None) -> str:
        """
        Full agent pipeline: Plan → Execute → (optionally Critique).
        Can chain multiple steps for complex queries.
        Returns tool context to inject into the system prompt.
        """
        plan = self.plan(message, context)
        logger.info(f"Agent plan: {plan}")

        if plan["tool"] == "none":
            return ""  # No tool needed — let normal LLM handle it

        # Execute the tool
        result = self.execute(plan, message)

        if not result:
            return ""

        # Optional critique (refine the raw output)
        if self.critic_enabled:
            result = self.critique(result, message)

        # Format as context for the LLM
        return self._format_tool_context(plan["tool"], result, plan.get("query", ""))

    # ─── TOOL EXECUTORS ─────────────────────────────────────────────

    def _exec_multi_search(self, query: str, topic: str = "") -> str:
        """Combine results from multiple intelligence sources with self-healing fallbacks."""
        logger.info(f"Agent executing Multi-Source Research: {query}")
        
        results = []
        
        # 1. Primary: Web Search
        try:
            web_res = self._exec_web_search(query)
            if web_res and "Error" not in web_res:
                results.append(f"--- SOURCE: WEB SEARCH ---\n{web_res}")
        except Exception as e:
            logger.warning(f"Multi-Search: Web failed, falling back. Error: {e}")

        # 2. Secondary: News Feeds
        try:
            news_res = self._exec_news(topic or query)
            if news_res and "No news found" not in news_res:
                results.append(f"--- SOURCE: NEWS FEEDS ---\n{news_res}")
        except Exception as e:
            logger.warning(f"Multi-Search: News failed. Error: {e}")

        # 3. Final Fallback: Internal Knowledge
        if not results:
            logger.info("Multi-Search: All external sources failed. Using base intelligence.")
            return f"I couldn't find live data for '{query}' due to a temporary network issue. Based on my general knowledge, I can provide limited info or you can try again later."
        
        return "\n\n".join(results)

    def _refine_intent(self, text: str) -> str:
        """Sanitize and normalize user input to improve tool routing accuracy."""
        # Strip common AI 'fillers' or polite prefixes if they are too long
        text = text.strip()
        
        # Remove common conversational noise patterns
        noise_patterns = [
            r"^(hey|hi|hello|jarvis|ai|please|can you|could you|i want you to)\s+",
            r"\s+(please|thank you|thanks|if you can)$"
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            
        return text.strip()

    def _exec_web_search(self, query: str) -> str:
        """Execute web search and return formatted results."""
        # Check if it's a news query
        is_news = any(kw in query.lower() for kw in ["news", "headlines", "breaking", "updates"])

        if is_news:
            results = self.web_search.search_news(query)
        else:
            results = self.web_search.search_text(query)

        if not results:
            return ""

        output = ""
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            source = r.get("source", "")
            date = r.get("date", "")

            output += f"{i}. {title}\n"
            if source:
                output += f"   Source: {source}\n"
            if date:
                output += f"   Date: {date}\n"
            if snippet:
                output += f"   {snippet[:250]}\n"
            output += "\n"

        return output

    def _exec_news(self, topic: str) -> str:
        """Execute news search via web search news endpoint."""
        results = self.web_search.search_news(topic)
        if not results:
            # Fallback to text search
            results = self.web_search.search_text(f"{topic} news latest")

        if not results:
            return ""

        output = ""
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            source = r.get("source", "")
            snippet = r.get("snippet", "")
            date = r.get("date", "")

            output += f"{i}. {title}"
            if source:
                output += f" ({source})"
            if date:
                output += f" [{date}]"
            output += "\n"
            if snippet:
                output += f"   {snippet[:200]}\n"
            output += "\n"

        return output

    def _exec_scrape(self, url: str) -> str:
        """Scrape a web page using neural extraction."""
        try:
            content = self.web_search.scrape_url(url)
            return content[:5000] if content else "Could not extract content."
        except Exception as e:
            return f"Scrape error: {e}"

    def _exec_deep_research(self, query: str) -> str:
        """
        Autonomous Multi-Step Research Loop.
        Step 1: Search. Step 2: Select top link. Step 3: Scrape & Summarize.
        """
        logger.info(f"Agent starting DEEP RESEARCH: {query}")
        
        # Step 1: Broad Search
        results = self.web_search.search_text(query, max_results=3)
        if not results:
            return "No initial results found for deep research."
        
        report = "--- DEEP RESEARCH OVERVIEW ---\n\n"
        
        # Step 2: Scrape the top most relevant result for deep context
        top_url = results[0]["url"]
        logger.info(f"Research Loop: Scrapping primary source {top_url}")
        
        primary_content = self.web_search.scrape_url(top_url)
        if primary_content and len(primary_content) > 100:
            report += f"--- PRIMARY SOURCE ANALYSIS ({results[0]['title']}) ---\n"
            report += primary_content[:3000] + "\n\n"
        
        # Step 3: Add snippets from other sources for breadth
        report += "--- CROSS-REFERENCE DATA ---\n"
        for r in results[1:]:
            report += f"- {r['title']}: {r['snippet']}\n"
            
        return report

    def _exec_gen_image(self, prompt: str) -> str:
        """Create multiple HD image variations."""
        try:
            from core.image_engine import ImageGenerator
            gen = ImageGenerator()
            
            # Generate 3 variations for Midjourney Pro feel
            results = []
            for i in range(3):
                res = gen.generate(f"{prompt} variation {i+1}")
                if res["status"] == "success":
                    results.append(res)
            
            if results:
                # Return string identifying all 3 paths/URLs
                out = "SUCCESS: HD Image variations generated.\n"
                for i, r in enumerate(results, 1):
                    out += f"IMAGE_{i}: {r['path']} | URL: {r['url']}\n"
                return out
            
            return "ERROR: Image generation failed."
        except Exception as e:
            return f"ERROR: Image engine failure: {e}"

    def _exec_edit_image(self, prompt: str, image_path: str = None) -> str:
        """Edit an image."""
        try:
            from core.image_engine import ImageGenerator
            gen = ImageGenerator()
            # If path isn't provided, we look for 'input.png' as default (handled by bot)
            path = image_path or os.path.join(config.DATA_DIR, "input.png")
            if not os.path.exists(path):
                return "ERROR: No image found to edit. Please send an image first."
            
            res = gen.edit(prompt, path)
            if res["status"] == "success":
                return f"SUCCESS: Image edited successfully. File: {res['filename']}. URL: {res['url']}"
            return f"ERROR: Image editing failed: {res.get('message')}"
        except Exception as e:
            return f"ERROR: Image engine failure: {e}"

    def _exec_gen_video(self, prompt: str) -> str:
        """Create an AI video."""
        try:
            from core.video_engine import VideoGenerator
            gen = VideoGenerator()
            res = gen.generate(prompt)
            if res["status"] == "success":
                return f"{res['message']} Link: {res['url']}"
            return f"ERROR: Video generation failed: {res.get('message')}"
        except Exception as e:
            return f"ERROR: Video engine failure: {e}"

    def _exec_manage_missions(self, message: str) -> str:
        """Interface with the Stark Task Engine to manage user missions."""
        from core.task_engine import TaskEngine
        engine = TaskEngine()
        
        msg = message.lower()
        
        # 1. Detect: Complete/Finish
        if any(kw in msg for kw in ["complete", "finish", "done", "clear"]):
            # Extract ID if possible
            match = re.search(r'mission\s+(\d+)', msg)
            if match:
                res = engine.complete_mission(int(match.group(1)))
                return "Mission marked as completed in the logs." if res["status"] == "success" else res["message"]
            return "Mission status updated."

        # 2. Detect: List/Show
        if any(kw in msg for kw in ["show missions", "list missions", "what are my missions", "agenda"]):
            missions = engine.list_active_missions()
            if not missions: return "Your agenda is currently clear, Stark."
            out = "--- CURRENT OPERATIONAL MISSIONS ---\n"
            for m in missions:
                priority = ["!", "!!", "!!!"][m['priority']-1]
                out += f"[{m['id']}] {priority} {m['title']} | {m['status']}\n"
            return out

        # 3. Default: Add Mission
        # Extract title (everything after 'add mission' or 'remind me to')
        title = message
        for pref in ["add mission", "remind me to", "task:"]:
            if pref in msg:
                title = message[msg.find(pref)+len(pref):].strip()
                break
        
        res = engine.add_mission(title)
        return f"Mission Synchronized: '{title}'. ID: {res.get('id')}"

    def _exec_os_control(self, message: str) -> str:
        """Handle Windows OS operations via the OSEngine."""
        from core.os_engine import os_engine
        msg = message.lower()
        
        # 1. Health Audit
        if any(kw in msg for kw in ["health", "status", "cpu", "ram", "memory", "stats"]):
            return os_engine.get_system_health()
            
        # 2. Process Audit
        if any(kw in msg for kw in ["running", "processes", "apps list", "audit"]):
            return os_engine.list_processes()
            
        # 3. App Launch
        launch_keywords = ["open ", "launch ", "start "]
        for kw in launch_keywords:
            if kw in msg:
                app_name = message[msg.find(kw)+len(kw):].strip("?.,! ")
                return os_engine.launch_app(app_name)
        
        return "I can check system health, list running apps, or launch applications. What do you need?"

    def _exec_file_mastery(self, message: str) -> str:
        """Execute complex file operations via OSEngine."""
        from core.os_engine import os_engine
        msg = message.lower()
        
        # 1. Organization
        if any(kw in msg for kw in ["clean", "organize", "sort"]):
            return os_engine.organize_directory()
            
        # 2. Deep Search
        if any(kw in msg for kw in ["find", "search", "lookup"]):
            # Extract pattern
            pattern = message
            for p in ["find file", "search for file", "find", "search"]:
                if p in msg:
                    pattern = message[msg.find(p)+len(p):].strip("?.,! \"'")
                    break
            return os_engine.deep_search(pattern)
            
        # 3. Summarization
        if any(kw in msg for kw in ["summarize", "whats in", "read"]):
            # For summarization, we need a path. 
            # If user didn't give a path, we might need to search first or ask.
            # Here we try to extract a path or filename
            target = self._extract_filepath(message)
            if target:
                return os_engine.summarize_file(target)
            return "Please provide the file name or path you'd like me to summarize."
        
        return "I can organize your desktop, search for files across your system, or summarize document content. What's the target?"

    def _exec_system_guardian(self, message: str) -> str:
        """Execute laptop system scans, threat auditing, and OS repairs."""
        try:
            import platform
            from datetime import datetime
            from core.system_guardian import system_guardian
            msg = message.lower()
            
            # Determine if this is a fix/repair intent or a scan intent
            is_fix = any(kw in msg for kw in ["fix", "solve", "repair", "remediate", "clean", "purge", "flush", "kill", "terminate"])
            
            # Run scan first
            sec_scan = system_guardian.audit_security_status()
            bug_scan = system_guardian.audit_system_bugs()
            
            aggregated_results = {
                "security": sec_scan,
                "bugs": bug_scan
            }
            
            report = []
            report.append("# JARVIS SYSTEM GUARDIAN DIAGNOSTIC REPORT")
            report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Operating System: {platform.system()} ({platform.release()})")
            report.append("-" * 50)
            
            if is_fix:
                report.append("## Remediating Threats and OS Bugs...")
                fix_results = system_guardian.resolve_threats_and_bugs(aggregated_results)
                if fix_results.get("success"):
                    report.append("### Actions Executed successfully:")
                    for action in fix_results.get("actions", []):
                        report.append(f"- [✓] {action}")
                else:
                    report.append("### No actions executed or remediation skipped.")
                
                if fix_results.get("errors"):
                    report.append("### Remediation Warnings:")
                    for err in fix_results.get("errors", []):
                        report.append(f"- [!] {err}")
                report.append("-" * 50)
            
            # Diagnostic details
            report.append("## 🛡️ Security Audit Status")
            report.append(f"Overall Status: **{sec_scan.get('status', 'UNKNOWN')}**")
            report.append(f"Windows Defender Active: {sec_scan.get('defender_active')}")
            report.append(f"Windows Firewall Active: {sec_scan.get('firewall_active')}")
            
            p_details = sec_scan.get('protection_details', {})
            if p_details:
                report.append("Protection Details:")
                for k, v in p_details.items():
                    report.append(f"  - {k}: {'Enabled' if v else 'Disabled'}")
            
            suspicious_keys = sec_scan.get('suspicious_startup_keys', [])
            if suspicious_keys:
                report.append(f"Suspicious Startup Registry Keys ({len(suspicious_keys)}):")
                for key in suspicious_keys:
                    report.append(f"  - '{key.get('name')}' -> `{key.get('path')}`")
            
            suspicious_procs = sec_scan.get('suspicious_processes', [])
            if suspicious_procs:
                report.append(f"Suspicious Processes Detected ({len(suspicious_procs)}):")
                for proc in suspicious_procs:
                    report.append(f"  - PID {proc.get('pid')}: {proc.get('name')} ({proc.get('reason')})")
            
            report.append("-" * 50)
            report.append("## 🐛 OS Health & Bug Audit")
            report.append(f"Overall Status: **{bug_scan.get('status', 'UNKNOWN')}**")
            report.append(f"Temporary Storage Bloat: {bug_scan.get('bloat_size_mb', 0)} MB")
            
            hogs = bug_scan.get('resource_hogs', [])
            if hogs:
                report.append(f"Resource Hogs Detected ({len(hogs)}):")
                for hog in hogs:
                    report.append(f"  - PID {hog.get('pid')}: {hog.get('name')} (CPU: {hog.get('cpu')}, RAM: {hog.get('mem')})")
            
            errors = bug_scan.get('event_log_errors', [])
            if errors:
                report.append(f"Recent OS / Driver Errors in Event Logs ({len(errors)}):")
                for err in errors:
                    report.append(f"  - [{err.get('time')}] {err.get('source')}: {err.get('message')}")
            
            broken_paths = bug_scan.get('broken_env_paths', [])
            if broken_paths:
                report.append(f"Missing PATH Directory Warnings ({len(broken_paths)}):")
                for path in broken_paths:
                    report.append(f"  - Missing: `{path}`")
                    
            if sec_scan.get('warnings') or bug_scan.get('warnings'):
                report.append("-" * 50)
                report.append("## ⚠️ Warnings Summary")
                all_warnings = sec_scan.get('warnings', []) + bug_scan.get('warnings', [])
                for w in all_warnings:
                    report.append(f"- {w}")
                    
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"SystemGuardian Executor Failure: {e}")
            return f"Error executing system guardian: {e}"

    # ─── HELPER METHODS ─────────────────────────────────────────────

    def _is_greeting(self, msg: str) -> bool:
        """Check if message is a simple greeting."""
        words = msg.strip().split()
        if len(words) > 4:
            return False
        return any(g in msg for g in GREETING_PATTERNS)

    def _is_factual_question(self, msg: str) -> bool:
        """Check if the message is a factual question that would benefit from search."""
        question_starts = [
            "who ", "what ", "where ", "when ", "why ", "how ",
            "is ", "are ", "was ", "were ", "did ", "does ", "do ",
            "can ", "will ", "which ",
        ]
        if any(msg.startswith(q) for q in question_starts):
            return len(msg.split()) >= 4
        return False

    def _extract_topic(self, message: str) -> str:
        """Extract the main topic from a user message."""
        msg = message.lower()

        # Remove common prefixes
        remove = [
            "latest news about", "latest news on", "latest news of",
            "news about", "news of", "news on",
            "tell me about", "search for", "search about",
            "find information about", "look up",
            "what is", "who is", "where is",
        ]
        for prefix in remove:
            if msg.startswith(prefix):
                msg = msg[len(prefix):].strip()
                break

        # Clean up
        msg = msg.strip("?.,! ")
        return msg if msg else message

    def _extract_code(self, message: str) -> str:
        """Extract code block from message."""
        # Look for code blocks
        code_match = re.search(r'```(?:python)?\s*\n?(.*?)```', message, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return ""

    def _extract_filepath(self, message: str) -> str:
        """Extract file path from message."""
        # Look for file paths
        path_match = re.search(r'["\']?([a-zA-Z]:\\[^\s"\']+|/[^\s"\']+)["\']?', message)
        if path_match:
            return path_match.group(1)
        # Look for simple filenames
        file_match = re.search(r'(?:read|open|show|cat)\s+(\S+\.\w+)', message.lower())
        if file_match:
            return file_match.group(1)
        return ""

    def _extract_file_write(self, message: str) -> tuple:
        """Extract filepath and content for write operations."""
        # Pattern: save "content" to filename.txt
        match = re.search(r'save\s+["\'](.+?)["\']\s+(?:to|as)\s+(\S+)', message, re.IGNORECASE)
        if match:
            return match.group(2), match.group(1)
        return "", ""

    def _extract_math(self, message: str) -> str:
        """Extract a math expression from the message."""
        # Remove common prefixes
        msg = message.lower()
        for prefix in ["calculate", "compute", "evaluate", "solve", "what is"]:
            if msg.startswith(prefix):
                msg = msg[len(prefix):].strip()
                break
        # Clean
        msg = msg.strip("?.,! ")
        return msg if msg else ""

    def _format_tool_context(self, tool: str, result: str, query: str) -> str:
        """Format tool output as context for the LLM system prompt."""
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        tool_labels = {
            "web_search": "LIVE WEB SEARCH RESULTS",
            "news_feed": "LIVE NEWS RESULTS",
            "web_scrape": "SCRAPED WEB CONTENT",
            "run_code": "CODE EXECUTION OUTPUT",
            "read_file": "FILE CONTENTS",
            "write_file": "FILE OPERATION RESULT",
            "calculate": "CALCULATION RESULT",
            "datetime": "CURRENT DATE/TIME",
            "system_guardian": "LAPTOP GUARDIAN REPORT",
        }

        label = tool_labels.get(tool, "TOOL OUTPUT")

        context = f"\n--- {label} (real-time) ---\n"
        context += f"Query: \"{query}\"\n"
        context += f"Retrieved: {now}\n\n"
        context += result.strip()
        context += f"\n--- END {label} ---\n"
        context += (
            "IMPORTANT: Use the above data to answer the user's question directly. "
            "Present it naturally. Cite sources briefly. "
            "Do NOT say you cannot access real-time data.\n"
        )

        return context
