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
        logger.info("Brain Node: Central Intelligence Loop Active.")

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
            return "Konnichiwa, Stark. Japanese protocol active."
        elif any(x in msg_lower for x in ["speak in english", "english mein", "english bolie"]):
            session["lang"] = "en"
            return "English protocol restored."

        # --- 3. Anti-Wikipedia Control ---
        if self._is_repeat(user_id, message):
            return "You already asked that, Stark. Should I dig deeper or change topics?"

        # --- 4. Modular Mission Execution ---
        
        # A. NEWS MODE: Strict Format + Real Data
        if task_mode == "news":
            news_query = f"latest {msg_lower.replace('news', '').strip()} news {datetime.now().strftime('%B %Y')}"
            intel = self.agent.run(news_query, user=user_id)
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "MANDATORY FORMAT: Step 1: [Headline], Step 2: [Explanation], Step 3: [Impact].\n"
                "Instruction: Summarize the following news data strictly in the 3-Step format. No sarcasm.\n\n"
                f"Data: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "formal", has_data=True)

        # B. LEARNING MODE: Mentor Style
        elif task_mode == "learn":
            intel = self.agent.run(message, user=user_id)
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: Teach this topic step-by-step. Keep it simple, like a British mentor.\n"
                "One small lesson at a time. No long history lectures.\n\n"
                f"Context: {intel}"
            )
            return self._finalize_synthesis(prompt, message, "assistant", has_data=True)

        # C. CHAT MODE: Intelligent Peer
        else:
            intel = self.agent.run(message, user=user_id)
            prompt = (
                f"REPLY IN {session['lang']}.\n"
                "Instruction: Respond as JARVIS—intelligent, British peer. Be concise and slightly witty."
            )
            if intel:
                prompt += f"\n\nContext found: {intel}"
            
            return self._finalize_synthesis(prompt, message, mode, has_data=bool(intel))

    def _detect_task_mode(self, text: str, current_mode: str) -> str:
        """Categorizes the user intent into specialized modular buckets."""
        if any(x in text for x in ["news", "headlines", "latest update"]):
            return "news"
        elif any(x in text for x in ["teach me", "learn", "how to"]):
            return "learn"
        elif current_mode == "savage" or "protocol 000" in text:
            return "savage"
        return "chat"

    def _finalize_synthesis(self, custom_prompt: str, user_msg: str, persona_key: str, has_data: bool = False) -> str:
        """Performs the final LLM call with a mode-specific system prompt."""
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
            
            history = [{"role": "user", "content": user_msg}]
            model_name = self.model.route_model(user_msg)
            
            response = self.model.generate(
                messages=history,
                system_prompt=full_system,
                model=model_name
            )
            
            # Cleanup and finalize
            import re
            response = re.sub(r"(as an ai|language model|developed by).*", "", response, flags=re.IGNORECASE)
            return self._apply_human_style(response.strip(), persona_key, emotion, has_data)
                
        except Exception as e:
            error_details = str(e)
            logger.error(f"Brain Node: Synthesis failure: {error_details}")
            return f"I've encountered a neural synthesis error, Stark. Details: {error_details}"

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
        """🎨 Neural Style Junction: Injects personality, emotion, and conversational variety."""
        import random
        
        # 1. Linguistic Detection (Hinglish Support)
        is_hindi = any(word in response.lower() for word in ["hai", "hoon", "aap", "main", "kya", "theek"])
        
        # 2. Emotional Response Node (Direct/Savage handling)
        if emotion == "angry" and not has_data:
            savage_responses = [
                "Understood. I'll recalibrate. No need to get your circuits in a twist, Boss.",
                "Ouch. That hit a neural buffer. Recalibrating logic...",
                "Noted. I'll do better. Even Stark had bugs in Mark I.",
                "Sarcasm detected. I'll step it up."
            ]
            if is_hindi:
                savage_responses = ["Theek hai, Boss. Recalibrate kar raha hoon. Gussa mat kijiye.", "Noted. Main aur behtar karunga."]
            return random.choice(savage_responses)

        # 3. Tone Switching Fillers (Reduced frequency for data missions)
        filler_chance = 0.25 if not has_data else 0.05
        if random.random() < filler_chance:
            eng_fillers = ["Right.", "On it, Stark.", "Checking the grid...", "Neural link stable.", "Here's the data."]
            hin_fillers = ["Theek hai.", "On it, Boss.", "Grid check kar raha hoon.", "Neural link stable hai.", "Ye raha data."]
            fill_pool = hin_fillers if is_hindi else eng_fillers
            response = f"{random.choice(fill_pool)} {response}"
            
        # 4. Proactive Closures (Disabled for structured data missions)
        if not has_data and "?" not in response and random.random() < 0.15:
            eng_closers = ["Should I dig deeper?", "Need more context?", "Anything else?"]
            hin_closers = ["Aur kuch detail chahiye?", "More context chahiye?", "Agla mission?"]
            cl_pool = hin_closers if is_hindi else eng_closers
            response = f"{response} \n\n{random.choice(cl_pool)}"
                
        return response





