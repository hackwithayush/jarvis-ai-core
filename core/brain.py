"""
Jarvis Brain — Central Intelligence Node
The unified 'One Brain' that powers Web, Telegram, and Voice.
"""
import logging
from typing import Optional
from datetime import datetime

import config
from core.model_manager import ModelManager

logger = logging.getLogger(__name__)

class JarvisBrain:
    """
    The central intelligence junction. 
    It bridges the AgentEngine with all manifestation interfaces.
    """

    def __init__(self, agent):
        self.agent = agent
        self.model = ModelManager()
        self.last_messages = {} # Anti-Wikipedia Loop
        self.sessions = {}      # Session Node: Language & Tone Memory 
        self.history = {}       # Multi-turn conversation history: user_id -> list of messages
        logger.info("Brain Node: Central Intelligence Loop Active.")

    def get_history(self, user_id: str, max_messages: int = 10) -> list:
        """Retrieve recent conversation history for conversational continuity."""
        if user_id not in self.history:
            self.history[user_id] = []
        return self.history[user_id][-max_messages:]

    def append_history(self, user_id: str, role: str, content: str, max_stored: int = 20):
        """Record turn to memory buffer."""
        if user_id not in self.history:
            self.history[user_id] = []
        clean_content = content.strip()
        if clean_content:
            self.history[user_id].append({"role": role, "content": clean_content})
            if len(self.history[user_id]) > max_stored:
                self.history[user_id] = self.history[user_id][-max_stored:]

    def process(self, message: str, user_id: str = "global", conv_id: Optional[str] = None, mode: str = "normal"):
        """
        Modular Process Node: Detects mission type and executes specialized protocols.
        """
        # --- 0. Session Initialization ---
        if user_id not in self.sessions:
            self.sessions[user_id] = {"lang": "en", "persona": "normal"}
        session = self.sessions[user_id]

        msg_lower = message.lower().strip()
        
        # --- 1. Modular Task Detection ---
        task_mode = self._detect_task_mode(msg_lower, mode)
        logger.info(f"Brain Node: Mission Detected -> {task_mode.upper()} Protocol.")

        # --- 2. Linguistic Presence Check ---
        if any(x in msg_lower for x in ["speak in japanese", "japanese mein", "japanese bolie"]):
            session["lang"] = "ja"
            resp = "Konnichiwa, Stark. Japanese protocol active."
            self.append_history(user_id, "user", message)
            self.append_history(user_id, "assistant", resp)
            return resp
        elif any(x in msg_lower for x in ["speak in english", "english mein", "english bolie"]):
            session["lang"] = "en"
            resp = "English protocol restored."
            self.append_history(user_id, "user", message)
            self.append_history(user_id, "assistant", resp)
            return resp

        # --- 3. Anti-Wikipedia Control ---
        if self._is_repeat(user_id, message):
            return "You already asked that, Stark. Should I dig deeper or change topics?"

        # --- 4. Modular Mission Execution with Safe Fallback ---
        intel = ""

        # Check for instant real-time market / forex feed
        fx_intel = ""
        try:
            from core.web_search import WebSearchEngine
            fx_intel = WebSearchEngine.get_live_fx_quote(message) or ""
        except Exception as e:
            logger.debug(f"FX quote check skipped: {e}")

        try:
            if task_mode == "news":
                news_query = f"latest {msg_lower.replace('news', '').strip()} news {datetime.now().strftime('%B %Y')}"
                intel = self.agent.run(news_query, user=user_id)
            elif task_mode == "learn":
                intel = self.agent.run(message, user=user_id)
            else:
                intel = self.agent.run(message, user=user_id)
        except Exception as e:
            logger.warning(f"Agent reasoning warning (non-fatal): {e}")
            intel = ""

        if fx_intel:
            intel = (fx_intel + "\n" + intel).strip() if intel else fx_intel
        
        # A. NEWS MODE: Strict Format + Real Data
        if task_mode == "news":
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "MANDATORY FORMAT: Step 1: [Headline], Step 2: [Explanation], Step 3: [Impact].\n"
                "Instruction: Summarize the following news data strictly in the 3-Step format. No sarcasm.\n\n"
                f"Data: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "formal", user_id=user_id, has_data=True)

        # B. LEARNING MODE: Mentor Style
        elif task_mode == "learn":
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: Teach this topic step-by-step. Keep it simple, like a British mentor.\n"
                "One small lesson at a time. No long history lectures.\n\n"
                f"Context: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "assistant", user_id=user_id, has_data=True)

        # D. SECURITY SCAN MODE: Deep Audit & Defensive Hardening
        elif task_mode == "security":
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: Conduct a rigorous cybersecurity audit and defensive review. Format with:\n"
                "1. 🔴 Vulnerability & Threat Findings (Severity: CRITICAL / HIGH / MEDIUM / LOW)\n"
                "2. 🔍 Attack Vector & Impact Analysis\n"
                "3. 🛡️ Remediation Patch & Hardened Code Implementation\n"
                "4. 📋 Security Hardening Checklist & Best Practices.\n\n"
                f"Context / Intel: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "security", user_id=user_id, has_data=bool(intel))

        # E. CODE FORGE MODE: Elite Software Engineering
        elif task_mode == "code":
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: You are in Code Forge mode. Deliver production-grade, bug-free, fully typed and tested code. "
                "Include edge-case handling, performance considerations, and clear architectural rationale.\n\n"
                f"Context / Intel: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "code", user_id=user_id, has_data=bool(intel))

        # F. INTEL RESEARCH MODE: Structured Intelligence Briefings
        elif task_mode == "research":
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: Synthesize a structured Executive Intelligence Briefing based on real-time data and cross-source analysis:\n"
                "📌 Executive Summary\n"
                "📊 Key Findings & Evidence\n"
                "⚖️ Comparative Source Analysis\n"
                "🧭 Strategic Implications & Actionable Next Steps.\n\n"
                f"Context / Intel: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "research", user_id=user_id, has_data=bool(intel))

        # G. CREATIVE CORE MODE: Generative & Aesthetic Foundry
        elif task_mode == "creative":
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: Apply creative direction, vivid narrative development, and aesthetic mastery. "
                "Provide compelling copy, imaginative ideas, scripts, or vivid visual prompts.\n\n"
                f"Context / Intel: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "creative", user_id=user_id, has_data=bool(intel))

        # H. AI MODE: Autonomous Routing Protocol
        elif task_mode == "ai":
            msg_lower = message.lower()
            has_security = any(w in msg_lower for w in ["vulnerabilit", "security", "audit", "exploit", "cve", "sanitize", "threat", "insecure"])
            has_code = any(w in msg_lower for w in ["fix", "bug", "code", "refactor", "patch", "implement", "python", "script"])

            if has_security and has_code:
                prompt = (
                    f"REPLY IN {session['lang']}.\n"
                    "⚡ AUTONOMOUS ROUTING PROTOCOL: Security Scan ➔ Code Forge ➔ Neural Chat\n"
                    "Autonomously orchestrate the complete solution across the three phases without asking the user to switch modes:\n"
                    "Phase 1 [🛡️ SECURITY SCAN]: Thoroughly audit the code/system for vulnerabilities, risks, and insecure patterns with severity ratings.\n"
                    "Phase 2 [⚙️ CODE FORGE]: Write complete, hardened, production-grade code that fixes every identified vulnerability and bug.\n"
                    "Phase 3 [💬 NEURAL CHAT / BRIEFING]: Provide an articulate, conversational explanation of the changes made, security implications, and testing instructions.\n\n"
                    f"Context / Intel: {intel}"
                )
            elif any(w in msg_lower for w in ["research", "investigate", "compare", "latest"]) and not has_code:
                prompt = (
                    f"REPLY IN {session['lang']}.\n"
                    "⚡ AUTONOMOUS ROUTING PROTOCOL: Intel Research\n"
                    "Autonomously deliver an executive intelligence briefing synthesizing real-time data.\n\n"
                    f"Context / Intel: {intel}"
                )
            else:
                prompt = (
                    f"REPLY IN {session['lang']}.\n"
                    "Instruction: You are JARVIS in [🧠 AI Mode - Autonomous Router]. Automatically choose and synthesize the best capabilities across coding, security, research, creative, and conversation to fulfill the user's objective.\n\n"
                    f"Context / Intel: {intel}"
                )
            return self._finalize_synthesis(prompt, message, "ai", user_id=user_id, has_data=bool(intel))

        # C. CHAT MODE: Intelligent Peer
        else:
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: Respond as JARVIS—intelligent, British peer. Be concise, articulate, and slightly witty."
            )
            if intel:
                prompt += f"\n\nContext found: {intel}"
            
            return self._finalize_synthesis(prompt, message, mode if mode in config.PERSONALITY_PROMPTS else "normal", user_id=user_id, has_data=bool(intel))

    def _detect_task_mode(self, text: str, current_mode: str) -> str:
        """Categorizes the user intent into specialized modular buckets."""
        if current_mode in ["code", "creative", "security", "research", "chat", "ai"]:
            return current_mode
        if any(x in text for x in ["news", "headlines", "latest update"]):
            return "news"
        elif any(x in text for x in ["teach me", "learn", "how to"]):
            return "learn"
        elif current_mode == "savage" or "protocol 000" in text:
            return "savage"
        return "chat"

    def _finalize_synthesis(self, custom_prompt: str, user_msg: str, persona_key: str, user_id: str = "global", has_data: bool = False) -> str:
        """Performs the final LLM call with a mode-specific system prompt and conversational memory."""
        try:
            now = datetime.now().strftime("%B %d, %Y")
            identity = config.SYSTEM_PROMPT.format(current_date=now)
            
            # Mode-Specific Identity Layer
            persona = config.PERSONALITY_PROMPTS.get(persona_key, config.PERSONALITY_PROMPTS["normal"])
            
            # Dynamic Emotion Inject
            from core.emotion_engine import emotion_engine
            emotion = self._detect_emotion(user_msg)
            emotion_engine.update_mood(user_msg, emotion)
            mood_inject = emotion_engine.get_mood_persona_prompt()
            
            full_system = f"{identity}\n\n# PERSONALITY PROTOCOL:\n{persona}\n{mood_inject}\n\n# CURRENT MISSION:\n{custom_prompt}"
            
            # Conversational memory: inject recent context
            prior_history = self.get_history(user_id)
            history_payload = [m for m in prior_history if m.get("content")]
            history_payload.append({"role": "user", "content": user_msg})
            
            model_name = self.model.route_model(user_msg)
            
            response = self.model.generate(
                messages=history_payload,
                system_prompt=full_system,
                model=model_name
            )
            
            # Cleanup and finalize
            import re
            response = re.sub(r"(as an ai|language model|developed by).*", "", response, flags=re.IGNORECASE).strip()
            final_res = self._apply_human_style(response, persona_key, emotion, has_data)
            
            # Update memory buffer
            self.append_history(user_id, "user", user_msg)
            self.append_history(user_id, "assistant", final_res)
            return final_res
                
        except Exception as e:
            error_details = str(e)
            logger.error(f"Brain Node: Synthesis failure: {error_details}")
            return f"I've encountered a neural synthesis disruption, Boss. Details: {error_details}"

    def _is_repeat(self, user_id: str, message: str) -> bool:
        """🔍 Anti-Loop Logic: Detects if the user is stuck in a prompt spiral."""
        message = message.lower().strip()
        if self.last_messages.get(user_id) == message:
            return True
        self.last_messages[user_id] = message
        return False

    def _detect_intent(self, prompt: str) -> str:
        """🧠 Internal Intent Node: Classifies the mission depth."""
        prompt = prompt.lower().strip()
        words = prompt.split()

        if len(words) == 1:
            return "short"
        elif any(x in prompt for x in ["explain", "what is", "how", "why", "deep dive", "research"]):
            return "detailed"
        elif any(x in prompt for x in ["code", "python", "script", "bug", "fix"]):
            return "coding"
        
        return "normal"


    def _detect_emotion(self, text: str) -> str:
        """🎭 Sentiment Node: Detects user emotional state for tone matching."""
        text = text.lower()
        if any(x in text for x in ["angry", "hate", "ugh", "bad", "stop", "stupid"]):
            return "angry"
        elif any(x in text for x in ["sad", "depressed", "help", "alone", "miss"]):
            return "sad"
        elif any(x in text for x in ["happy", "great", "love", "awesome", "good", "thanks"]):
            return "happy"
        return "neutral"

    def _apply_human_style(self, response: str, mode: str, emotion: str = "neutral", has_data: bool = False) -> str:
        """🎨 Neural Style Junction: Cleans markdown formatting, preserves paragraphs, and enforces high-signal output."""
        import re
        if not response:
            return "Systems nominal, Boss. How can I assist?"
            
        # 1. Clean markdown and excessive newlines while preserving genuine paragraph breaks
        cleaned = re.sub(r"\r\n", "\n", response.strip())
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        
        # 2. Strip leftover AI meta-disclaimers
        cleaned = re.sub(r"^(As an AI|As an artificial intelligence)[,\s]*", "", cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()





