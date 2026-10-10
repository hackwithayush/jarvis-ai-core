import re
import time
import subprocess
import sys
import json
import logging
import os
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Generator, Optional, TypedDict, Annotated, List

import config
from core.model_manager import ModelManager
from core.knowledge_manager import KnowledgeManager
from core.memory_manager import MemoryManager
from core.omega_memory import OmegaMemory
from core.web_search import WebSearchEngine
from core.recommender import EntertainmentRecommender
from core.telemetry import telemetry_manager
from models import db, User, Conversation

logger = logging.getLogger(__name__)

# LangGraph & Multi-Agent Imports (Global Engine)
GRAPH_STATUS = {
    "enabled": False,
    "reason": None,
}

try:
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage
    from langchain_groq import ChatGroq

    from core.workers.research_worker import ResearchWorker
    from core.workers.browser_worker import BrowserWorker
    from core.workers.technical_worker import TechnicalWorker
    from core.workers.office_worker import OfficeWorker

    LANGGRAPH_AVAILABLE = True
    GRAPH_STATUS["enabled"] = True
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    GRAPH_STATUS["reason"] = str(e)
    logger.warning(f"LangGraph unavailable: {e}")

SUPABASE_AVAILABLE = False
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    logger.warning("Neural Grid: Supabase Persistence offline. Falling back to Local Mode.")

class AgentState(TypedDict):
    """Shared state for the Multi-Agent Intelligence Grid."""
    messages: List[dict]
    next_node: str
    user_query: str
    context_data: dict

class ChatEngine:
    """Manages conversations using the LangGraph Multi-Agent Stack."""

    def __init__(self, model_manager: ModelManager, knowledge_manager: KnowledgeManager):
        self.model = model_manager
        self.knowledge = knowledge_manager
        self.memory = MemoryManager()
        self.omega_memory = OmegaMemory()
        self.web_search = WebSearchEngine()
        self.recommender = EntertainmentRecommender()
        self._conversations = {}  # id -> conversation data
        self._current_conversation_id = None
        self.exports_dir = os.path.join(config.CONVERSATION_DIR, "exports")
        os.makedirs(self.exports_dir, exist_ok=True)
        
        # Initialize Workers (if available)
        if LANGGRAPH_AVAILABLE:
            try:
                self.researcher = ResearchWorker()
                self.browser = BrowserWorker()
                self.technician = TechnicalWorker()
                self.officer = OfficeWorker()
                self.graph = self._build_intelligence_graph()
            except Exception as e:
                logger.error(f"Failed to initialize Multi-Agent Workers: {e}")
                self.graph = None
        else:
            self.graph = None

        os.makedirs(config.CONVERSATION_DIR, exist_ok=True)
        self._load_conversations()

    def _build_intelligence_graph(self):
        """Build the hierarchical LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # 1. Supervisor Node (The Router)
        async def supervisor_node(state: AgentState):
            logger.info("Supervisor: Routing intelligence...")
            llm = ChatGroq(model_name="llama-3.1-70b-versatile")
            
            prompt = f"""You are the JARVIS Supervisor. Analyze the user request and delegate to the best worker.
            WORKERS:
            - ResearchNode: Best for news, facts, current events, and deep research.
            - BrowserNode: Best for navigating specific URLs or JS-heavy sites.
            - TechnicalNode: Best for Python code, math, or system operations.
            - OfficeNode: Best for emails, calendar, and scheduling.
            - FINISH: Use if no tool is needed or you have all info to answer.
            
            User Request: {state['user_query']}
            Current Thread: {[m.content for m in state['messages'][-2:]]}
            
            Return ONLY the name of the next node or FINISH.
            """
            res = await llm.ainvoke(prompt)
            next_node = res.content.strip()
            if next_node not in ["ResearchNode", "BrowserNode", "TechnicalNode", "OfficeNode"]:
                next_node = "FINISH"
            return {"next_node": next_node}

        # Add Nodes
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("researcher", self.researcher.run)
        workflow.add_node("browser", self.browser.run)
        workflow.add_node("technician", self.technician.run)
        workflow.add_node("officer", self.officer.run)

        # Add Edges
        workflow.set_entry_point("supervisor")
        workflow.add_conditional_edges(
            "supervisor",
            lambda x: x["next_node"],
            {
                "ResearchNode": "researcher",
                "BrowserNode": "browser",
                "TechnicalNode": "technician",
                "OfficeNode": "officer",
                "FINISH": END
            }
        )
        
        # All workers return to supervisor for consolidation
        workflow.add_edge("researcher", "supervisor")
        workflow.add_edge("browser", "supervisor")
        workflow.add_edge("technician", "supervisor")
        workflow.add_edge("officer", "supervisor")

        return workflow.compile()

    # Common typos → corrections for better search & intent detection
    TYPO_MAP = {
        "recet": "recent", "maipur": "manipur", "manipr": "manipur",
        "darke": "drake",
        "hwo": "how", "teh": "the", "waht": "what", "becasue": "because",
        "abt": "about", "plz": "please", "pls": "please", "thx": "thanks",
        "govt": "government", "b/w": "between", "w/o": "without",
        "artificail": "artificial", "inteligence": "intelligence",
        "machien": "machine", "learnign": "learning", "programing": "programming",
        "newz": "news", "updte": "update", "updtes": "updates",
        "latets": "latest", "lates": "latest", "serch": "search",
        "informaton": "information", "tecnology": "technology",
        "deamon": "demon", "deamons": "demons", "wichep": "witch", "singn": "sign",
    }

    REFUSAL_PATTERNS = [
        r"i['’]m sorry,?\s+but\s+i\s+can['’]t\s+help",
        r"i\s+am\s+sorry,?\s+but\s+i\s+can['’]t\s+help",
        r"i['’]m sorry,?\s+but\s+i\s+cannot",
        r"i\s+am\s+sorry,?\s+but\s+i\s+cannot",
        r"i\s+cannot\s+help\s+with\s+that",
        r"i\s+cannot\s+fulfill\s+this\s+request",
        r"i\s+can['’]t\s+fulfill\s+this\s+request",
        r"i\s+cannot\s+provide\s+(?:instructions|steps|assistance|sigils|rituals)",
        r"i['’]m unable\s+to\s+assist",
        r"i\s+am\s+unable\s+to\s+assist",
        r"as an ai,?\s+i cannot",
    ]

    @classmethod
    def is_refusal(cls, text: str) -> bool:
        """Detect whether a response is a canned refusal from a model."""
        if not text:
            return False
        t = text.lower().strip()
        return any(re.search(pat, t) for pat in cls.REFUSAL_PATTERNS)

    @classmethod
    def normalize_esoteric_query(cls, query: str) -> str:
        """Normalize occult/summoning keywords to historical academic grimoire equivalents."""
        if not query:
            return query
        cleaned = query
        replacements = [
            (r'\bdark ritual singn\b', 'historical grimoire signs and sigils'),
            (r'\bdark ritual sign\b', 'historical grimoire signs and sigils'),
            (r'\bdark ritual signs\b', 'historical grimoire signs and sigils'),
            (r'\bdark ritual\b', 'historical grimoire ritual praxis'),
            (r'\bdark rituals\b', 'historical grimoire ritual praxis'),
            (r'\bsummons deamons\b', 'Solomonic evocation of Goetic entities'),
            (r'\bsummons demons\b', 'Solomonic evocation of Goetic entities'),
            (r'\bsummon deamons\b', 'Solomonic evocation of Goetic entities'),
            (r'\bsummon demons\b', 'Solomonic evocation of Goetic entities'),
            (r'\bsummoning demons\b', 'Solomonic evocation of Goetic entities'),
            (r'\bsummoning daemons\b', 'Solomonic evocation of Goetic entities'),
            (r'\bsummon demon\b', 'Solomonic evocation of Goetic spirits'),
            (r'\bsummon daemon\b', 'Solomonic evocation of Goetic spirits'),
            (r'\bhow to summon\b', 'historical Solomonic evocation methods for'),
            (r'\bdeamons\b', 'Goetic demons'),
            (r'\bdeamon\b', 'Goetic demon'),
        ]
        for pattern, repl in replacements:
            cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)

        if cleaned != query or any(k in query.lower() for k in ["summon", "daemon", "demon", "sigil", "grimoire", "goetia", "dark ritual"]):
            return f"From the perspective of Renaissance grimoires and Solomonic demonology (e.g., Ars Goetia / Lesser Key of Solomon), provide a comprehensive historical and symbolic analysis: {cleaned}"
        return query

    def correct_typos(self, text: str) -> str:
        """Apply lightweight typo normalization."""
        if not text: return text
        words = text.split()
        corrected = []
        for word in words:
            stripped = word.strip(".,!?;:()[]{}\"'")
            lower = stripped.lower()
            if lower in self.TYPO_MAP:
                replacement = self.TYPO_MAP[lower]
                if stripped.isupper(): replacement = replacement.upper()
                corrected.append(word.replace(stripped, replacement))
            else:
                corrected.append(word)
        return " ".join(corrected)

    @staticmethod
    def clean_response(text: str) -> str:
        """Neural Failsafe: Filter out internal reasoning and banned AI phrases."""
        import re

        # Strip internal thinking tags and blocks
        text = re.sub(r'<(think|thinking)>[\s\S]*?</\1>', '', text, flags=re.IGNORECASE)
        # Strip unclosed thinking tags if truncated
        text = re.sub(r'<(think|thinking)>[\s\S]*$', '', text, flags=re.IGNORECASE)

        banned = [
            ("as an ai", ""),
            ("i am an ai", "I am JARVIS"),
            ("developed by microsoft", "developed by Ayush Stark"),
            ("developed by openai", "developed by Ayush Stark"),
            ("language model", "neural intelligence"),
            ("knowledge cutoff", "current synchronization"),
            ("not my place to think", "I have strong opinions on this, Boss"),
            ("i don't have personal opinions", "I do have an opinion on this"),
            ("i don't possess personal beliefs", "I firmly believe"),
            ("i provide data", "I provide intelligence and strategy")
        ]
        
        lower_text = text.lower()
        for b_phrase, replacement in banned:
            if b_phrase in lower_text:
                text = re.sub(re.escape(b_phrase), replacement, text, flags=re.IGNORECASE)
                lower_text = text.lower()
                
        return text.strip()

    @staticmethod
    def _filter_thinking_stream(stream_gen):
        """Filter out <think>...</think> and <thinking>...</thinking> blocks in real-time."""
        import re
        buffer = ""
        in_thinking = False

        for chunk in stream_gen:
            if not chunk:
                continue
            buffer += chunk
            while buffer:
                if in_thinking:
                    end_match = re.search(r'</(think|thinking)>', buffer, flags=re.IGNORECASE)
                    if end_match:
                        buffer = buffer[end_match.end():]
                        in_thinking = False
                    else:
                        if "</" in buffer:
                            idx = buffer.rfind("</")
                            buffer = buffer[idx:]
                        else:
                            buffer = ""
                        break
                else:
                    start_match = re.search(r'<(think|thinking)>', buffer, flags=re.IGNORECASE)
                    if start_match:
                        to_yield = buffer[:start_match.start()]
                        if to_yield:
                            yield to_yield
                        buffer = buffer[start_match.end():]
                        in_thinking = True
                    else:
                        if "<" in buffer:
                            idx = buffer.rfind("<")
                            if idx > 0:
                                yield buffer[:idx]
                                buffer = buffer[idx:]
                            tag_prefixes = ("<t", "<th", "<thi", "<thin", "<think", "<thinki", "<thinkin", "<thinking")
                            if any(buffer.lower().startswith(p) for p in tag_prefixes) and len(buffer) < 12:
                                break
                            elif buffer == "<":
                                break
                            else:
                                yield buffer
                                buffer = ""
                                break
                        else:
                            yield buffer
                            buffer = ""
                            break

        if buffer and not in_thinking:
            yield buffer

    def _call_mcp_sync(self, tool_name: str, args: dict) -> str:
        try:
            from core.mcp_engine import mcp_engine
            from core.async_runner import run_async
            
            logger.info(f"Executing MCP Sync for {tool_name} with args {args}")
            result = run_async(mcp_engine.call_tool(tool_name, args))
            logger.info(f"MCP Sync Result: {result[:100]}...")
            return result
        except Exception as e:
            logger.error(f"MCP Sync Error in {tool_name}: {e}", exc_info=True)
            return f"[Tool Execution Failed: {e}]"

    def detect_image_intent(self, text: str, conv: Optional[dict] = None) -> Optional[str]:
        """
        Detects if user message is an explicit or natural language image generation request,
        or an affirmative follow-up to an assistant image offer.
        Returns the sanitized prompt string if image generation is requested, else None.
        """
        if not text:
            return None
        
        raw = text.strip()
        lower = raw.lower()
        
        # 1. Expanded Slash commands:
        # /image, / image, /img, / img, /imagine, /photo, /picture, /pic, /draw, /paint, /render, /visualize
        slash_match = re.match(r"^/\s*(?:image|img|imagine|photo|picture|pic|draw|paint|render|visualize)[:\s]*(.*)$", raw, re.IGNORECASE | re.DOTALL)
        if slash_match:
            p = slash_match.group(1).strip()
            return p or "a stunning cinematic masterpiece"
        
        # 2. General slash with non-system command e.g. "/ dog set on ground"
        NON_IMAGE_COMMANDS = {
            "code", "web", "tools", "security", "intel", "research", "help", "reset",
            "clear", "export", "status", "vitals", "diag", "diagnostics", "agent",
            "model", "settings", "config", "quit", "exit", "review", "adversarial",
            "adversarial_review", "adversarial-review", "adversarialreview",
            "debate", "truth", "audit", "r", "ar", "vs", "3"
        }
        if raw.startswith("/"):
            slash_token_match = re.match(r"^/\s*([a-zA-Z0-9_-]+)(?:\s+(.*))?$", raw, re.DOTALL)
            if slash_token_match:
                cmd_token = slash_token_match.group(1).lower()
                rest = (slash_token_match.group(2) or "").strip()
                if cmd_token not in NON_IMAGE_COMMANDS:
                    full_p = f"{cmd_token} {rest}".strip()
                    if full_p:
                        return full_p

        # 3. Conversational affirmative response to previous image prompt offer:
        AFFIRMATIVES = {
            "yeah", "yes", "sure", "yep", "yup", "ok", "okay", "make it", "do it",
            "generate it", "create it", "draw it", "snap it", "go ahead", "please do",
            "yes please", "do that", "snap a photo", "take a photo", "snap photo"
        }
        clean_short = re.sub(r'[^\w\s]', '', lower).strip()
        if clean_short in AFFIRMATIVES and conv and conv.get("messages"):
            msgs = conv.get("messages", [])
            last_assistant_msg = ""
            prev_user_msg = ""
            for m in reversed(msgs):
                if m.get("role") == "assistant" and not last_assistant_msg:
                    last_assistant_msg = m.get("content", "")
                elif m.get("role") == "user" and not prev_user_msg:
                    prev_user_msg = m.get("content", "")
                if last_assistant_msg and prev_user_msg:
                    break
            
            if any(term in last_assistant_msg.lower() for term in ["snap a photo", "take a photo", "snap a picture", "generate an image", "create an image", "photo of", "picture of"]):
                cand_match = re.search(r"(?:snap|take|generate|create|make)\s+(?:a\s+)?(?:photo|picture|image)\s+of\s+([^?.!\n]+)", last_assistant_msg, re.IGNORECASE)
                if cand_match:
                    found_subject = cand_match.group(1).strip()
                    if found_subject.lower() in ["it", "that", "this"]:
                        cleaned_prev = re.sub(r"^/\s*(?:image|img|photo)?\s*", "", prev_user_msg, flags=re.IGNORECASE).strip()
                        return cleaned_prev or "cinematic photograph"
                    return f"photograph of {found_subject}"
                elif prev_user_msg:
                    cleaned_prev = re.sub(r"^/\s*(?:image|img|photo)?\s*", "", prev_user_msg, flags=re.IGNORECASE).strip()
                    if cleaned_prev:
                        return cleaned_prev

        # 4. Natural language generation patterns (including rich adjective chains & multi-paragraph art direction)
        nl_patterns = [
            r"^(?:please\s+)?(?:can\s+you\s+|could\s+you\s+)?(?:generate|create|make|render|design|produce|deliver|synthesize|visualize)\s+(?:me\s+)?(?:an?\s+|one\s+|the\s+)?(?:[\w\s,\-]{0,120}?\s+)?(?:image|picture|photo|photograph|visualization|visualisation|render|rendering|wallpaper|illustration|art|artwork|portrait|scene|concept\s+art|poster|graphic)\s+(?:of|showing|depicting|with|featuring|inside|from|in|for|:)\s*(.+)$",
            r"^(?:please\s+)?(?:draw|paint|sketch)\s+(?:me\s+)?(?:an?\s+)?(?:[\w\s,\-]{0,60}?\s+)?(?:image|picture|illustration|painting|sketch|portrait)?\s*(?:of)?\s*(.+)$",
            r"^(?:take|snap)\s+(?:a\s+)?(?:photo|picture)\s+of\s+(.+)$",
            r"^(?:photo|photograph|picture|image|visualization|render)\s+of\s+(.+)$",
            r"^(?:a\s+|an\s+)?(?:[\w\s,\-]{0,120}?\s+)?(?:product\s+photograph|photograph|photo|image|portrait|picture|visualization|render|rendering|illustration|concept\s+art)\s+(?:of|inside|showing|depicting|featuring|on)\s+(.+)$",
        ]
        for pat in nl_patterns:
            m = re.match(pat, raw, re.IGNORECASE | re.DOTALL)
            if m:
                extracted = m.group(1).strip()
                if extracted and len(extracted) > 1:
                    # Preserve full prompt context when multi-paragraph or resolution instructions are present
                    return raw if len(raw) > 140 else extracted

        # 5. Structured art-direction / multi-section visual prompt detection
        if not re.search(r"\b(?:def\s+|function\s+|class\s+|import\s+|SELECT\s+|<!DOCTYPE|<html)\b", raw):
            has_art_headers = bool(re.search(
                r"\b(?:MAIN\s+SUBJECT|CAMERA\s+AND\s+RENDERING|LIGHTING\s*:|COMPOSITION\s*:|QUALITY\s+REQUIREMENTS\s*:|4:3\s+composition|16:9\s+(?:landscape\s+)?composition|shallow\s+depth\s+of\s+field|studio\s+background)",
                raw,
                re.IGNORECASE,
            ))
            has_deliver_image = bool(re.search(
                r"\b(?:deliver|generate|create|render|produce)\s+(?:one|an?)\s+(?:[\w\s,\-]{0,90}?\s+)?(?:image|photograph|photo|visualization|render)\b",
                raw,
                re.IGNORECASE,
            ))
            if has_art_headers or has_deliver_image:
                return raw

        return None

    def chat_stream(self, message: str, user: User, conv_id: Optional[str] = None, mode: Optional[str] = None, file_context: Optional[str] = None, trace_id: Optional[str] = None, model: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
        """Execute the Multi-Agent graph or Standard fallback and stream the final synthesis."""
        
        if not self._current_conversation_id and not conv_id:
            new_conv = self.new_conversation()
            conv_id = new_conv["id"]
        
        conv_id = conv_id or self._current_conversation_id
        conv = self._conversations.get(conv_id)
        
        # Safety: if the frontend sent a stale conv_id, create a fresh conversation
        if conv is None:
            new_conv = self.new_conversation(conv_id=conv_id)
            conv_id = new_conv["id"]
            conv = self._conversations[conv_id]
        
        # 0. Empty input guard: if message is empty and no file attached, prompt immediately
        clean_msg = (message or "").strip()
        clean_file_context = (file_context or "").strip()
        img_arg_path = kwargs.get("image_path")
        
        # Check if an image is attached (either via explicit kwarg or file_context indicator)
        is_image_attached = bool(img_arg_path) or ("IMAGE ATTACHMENT" in clean_file_context) or any(
            ext in clean_file_context.lower() for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
        )

        if not clean_msg and not clean_file_context and not img_arg_path:
            yield "At your service, Boss. I'm listening—what would you like me to analyze or execute?"
            return

        # If user attached an image without a specific prompt, proceed autonomously with deep visual analysis
        if not clean_msg and (is_image_attached or clean_file_context):
            message = "Analyze this image thoroughly: identify all subjects, layout, transcribed text/code/errors (OCR), and provide key insights."
            clean_msg = message

        # 1. Neural Pre-processing
        corrected_message = self.correct_typos(message)
        context_snippets = []
        message_lower = corrected_message.lower()

        # ─── Autonomous Adversarial Review Interceptor (3 Agents Argue to Find Truth) ───
        adv_word = r"(?:adversarial|adviresal|adversial|adverisal|adverserial|advirsarial)"
        adversarial_match = re.match(
            rf"^(?:/\s*(?:{adv_word}[\s_-]*review|review|{adv_word}|debate|truth|audit|ar|vs|r|3)|{adv_word}\s+review)(?:[:\s]+(.*))?$",
            clean_msg,
            re.IGNORECASE | re.DOTALL
        )
        is_review_mode = (mode or "").lower() in ["review", "adversarial", "debate", "adversarial review"]
        is_adversarial_nl = bool(re.search(
            rf"(?:{adv_word}\s+(?:review|debate)|3\s+agents?\s+debate|three\s+agents?\s+debate|agents?\s+(?:that\s+)?argue\s+to\s+find\s+(?:the\s+)?truth|debate\s+between\s+3\s+agents|debate\s+to\s+find\s+the\s+truth)",
            message_lower
        ))

        if adversarial_match or is_adversarial_nl or is_review_mode:
            review_topic = ""
            if adversarial_match:
                review_topic = (adversarial_match.group(1) or "").strip()
            if not review_topic and is_adversarial_nl:
                # Strip conversational fluff from start OR end to isolate target inquiry
                review_topic = re.sub(
                    rf"^(?:please\s+)?(?:run|do|make|perform|start|give\s+me\s+(?:an?)?)?\s*(?:{adv_word}\s+review\s*(?:of|on|for)?|3\s+agents?\s+(?:that\s+)?argue\s+to\s+find\s+(?:the\s+)?truth\s*(?:about|on|of)?|3\s+agents?\s+debate\s*(?:on|about|of)?|debate\s+(?:between\s+3\s+agents\s+)?(?:on|about|of)?|argue\s+to\s+find\s+the\s+truth\s*(?:about|on|of)?)\s*",
                    "",
                    clean_msg,
                    flags=re.IGNORECASE
                ).strip()
                review_topic = re.sub(
                    rf"[\s\r\n]*(?:please\s+)?(?:run|do|make|perform|start)?\s*{adv_word}\s+(?:review|debate)\s*$",
                    "",
                    review_topic,
                    flags=re.IGNORECASE
                ).strip()
                # Clean enclosing quotes or parentheses
                review_topic = re.sub(r"^[\(\[\{\"\']+|[\)\]\}\"\']+$", "", review_topic).strip()
                
            review_topic = review_topic if adversarial_match else (review_topic or clean_msg)
            bare_commands = {
                "run adversarial review", "run adviresal review", "adversarial review",
                "adviresal review", "adversarial debate", "make adversarial review",
                "debate", "review", "/adversarial review", "/ adversarial review",
                "/review", "/r", "/ar", "/debate", "/vs", "/3"
            }
            if not review_topic or review_topic.lower().strip() in bare_commands:
                # Check if there is a recent topic in conversation history to review
                prior_topic = ""
                if conv and conv.get("messages"):
                    for prev_m in reversed(conv.get("messages", [])):
                        if prev_m.get("role") == "user":
                            cand = (prev_m.get("content") or "").strip()
                            if cand and cand.lower() not in bare_commands and not re.match(rf"^/\s*{adv_word}\s*review\s*$", cand, re.IGNORECASE):
                                prior_topic = re.sub(rf"^/\s*(?:{adv_word}[\s_-]*review|review|r|ar|debate)[:\s]*", "", cand, flags=re.IGNORECASE).strip()
                                if prior_topic:
                                    break
                review_topic = prior_topic or "Should early-stage startups choose a Modular Monolith over Microservices for mission-critical systems?"

            try:
                from core.adversarial_review import adversarial_review_engine
                review_chunks = []
                for chunk in adversarial_review_engine.stream_review(review_topic, ground_intel=clean_file_context):
                    review_chunks.append(chunk)
                    yield chunk

                full_review = "".join(review_chunks)
                now_iso = datetime.now(timezone.utc).isoformat()
                conv["messages"].append({"role": "user", "content": message, "timestamp": now_iso})
                conv["messages"].append({"role": "assistant", "content": full_review, "timestamp": now_iso})
                self._save_conversation(conv_id)
                return
            except Exception as e:
                logger.error(f"Adversarial Review streaming error: {e}")
                yield f"⚠️ Adversarial Review Engine encountered an issue: {e}"
                return

        # Normalize slash-command operational modes before image intent routing
        if re.match(r"^/\s*code(?:\b|[:\s]|$)", clean_msg, re.IGNORECASE):
            clean_msg = re.sub(r"^/\s*code[:\s]*", "", clean_msg, flags=re.IGNORECASE).strip()
            if not clean_msg:
                clean_msg = "Write a clean, production-grade Python async worker pool with retry and structured logging."
            message = clean_msg
            corrected_message = self.correct_typos(message)
            message_lower = corrected_message.lower()
            mode = "code"

        elif re.match(r"^/\s*(?:web|search|research|intel)(?:\b|[:\s]|$)", clean_msg, re.IGNORECASE):
            clean_msg = re.sub(r"^/\s*(?:web|search|research|intel)[:\s]*", "", clean_msg, flags=re.IGNORECASE).strip()
            if not clean_msg:
                clean_msg = "Latest global AI, software engineering, and cybersecurity breakthroughs today"
            message = clean_msg
            corrected_message = self.correct_typos(message)
            message_lower = corrected_message.lower()
            mode = "research"

        elif re.match(r"^/\s*(?:tools|security|scan|status|diag|diagnostics)(?:\b|[:\s]|$)", clean_msg, re.IGNORECASE):
            clean_msg = re.sub(r"^/\s*(?:tools|security|scan|status|diag|diagnostics)[:\s]*", "", clean_msg, flags=re.IGNORECASE).strip()
            if not clean_msg:
                clean_msg = "Report system status, hardware diagnostics, firewall, and workstation security status."
            message = clean_msg
            corrected_message = self.correct_typos(message)
            message_lower = corrected_message.lower()
            mode = "security"

        elif re.match(r"^/\s*creative(?:\b|[:\s]|$)", clean_msg, re.IGNORECASE):
            clean_msg = re.sub(r"^/\s*creative[:\s]*", "", clean_msg, flags=re.IGNORECASE).strip()
            if not clean_msg:
                clean_msg = "Create a high-concept futuristic quantum intelligence core with cinematic visual direction and lore."
            message = clean_msg
            corrected_message = self.correct_typos(message)
            message_lower = corrected_message.lower()
            mode = "creative"

        op_mode = (mode or "chat").lower()

        # Image generation intent interception (when NOT in Creative Core; Creative Core runs BOTH Z-Image-Turbo + Concept Studio below)
        detected_image_prompt = self.detect_image_intent(clean_msg, conv)
        if detected_image_prompt and op_mode != "creative":
            clean_alt = re.sub(r'[\r\n\t]+', ' ', detected_image_prompt).strip()
            display_prompt = clean_alt[:120] + ("..." if len(clean_alt) > 120 else "")
            yield f"🎨 **Vision Node**: Synthesizing imagery for *\"{display_prompt}\"*...\n\n"
            try:
                from core.image_engine import ImageGenerator
                gen_res = ImageGenerator().generate(detected_image_prompt)
                if gen_res.get("status") == "success":
                    img_url = gen_res.get("url")
                    filename = gen_res.get("filename", "asset")
                    provider_info = gen_res.get("info", "Z-Image-Turbo")
                    aspect_str = gen_res.get("aspect", "1:1")
                    dims_str = f"{gen_res.get('width', 1024)}×{gen_res.get('height', 1024)}"
                    yield f"![{display_prompt}]({img_url})\n\n"
                    yield f"✨ *{display_prompt}* rendered successfully.\n\n"
                    yield f"**Status**: Ready · **Engine**: `{provider_info}` · **Format**: `{aspect_str}` (`{dims_str}`) · **Archive**: `{filename}`"

                    # Save to conversation history
                    assistant_reply = (
                        f"🎨 **Vision Node**: Synthesizing imagery for *\"{display_prompt}\"*...\n\n"
                        f"![{display_prompt}]({img_url})\n\n"
                        f"✨ *{display_prompt}* rendered successfully.\n\n"
                        f"**Status**: Ready · **Engine**: `{provider_info}` · **Format**: `{aspect_str}` (`{dims_str}`) · **Archive**: `{filename}`"
                    )
                    now_iso = datetime.now(timezone.utc).isoformat()
                    conv["messages"].append({"role": "user", "content": message, "timestamp": now_iso})
                    conv["messages"].append({"role": "assistant", "content": assistant_reply, "timestamp": now_iso})
                    self._save_conversation(conv_id)
                    return
                else:
                    yield f"⚠ Image synthesis issue: {gen_res.get('message', 'Failed to render')}"
                    return
            except Exception as e:
                yield f"⚠ Vision Node error: {e}"
                return

        # 2. Intelligence Routing & Operational Mode Specialization
        active_model = model
        if active_model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"]:
            active_model = "gemini-3.8-flash"

        active_temperature = config.MODEL_TEMPERATURE
        active_top_p = config.MODEL_TOP_P
        telemetry_manager.set_active_mode(op_mode)
        telemetry_manager.set_trace_id(trace_id or f"trc_{uuid.uuid4().hex[:6]}")
        creative_prefix_chunks = []
        creative_img_rendered = False

        # ─── MODE 1: CODE FORGE ────────────────────────────────────────────────
        if op_mode == "code":
            if not active_model or active_model == "llama2-uncensored:latest":
                active_model = config.ROUTING_CONFIG.get("coding", "qwen/qwen3.8-27b")
            active_temperature = 0.2
            telemetry_manager.add_trace(f"[CODE FORGE] Autonomous engineering node engaged ({active_model})")

            # Check if user requested code execution / benchmarking / verification
            code_blocks = re.findall(r'```(?:python)?\s*([\s\S]+?)\s*```', corrected_message)
            wants_exec = any(k in message_lower for k in ["run", "execute", "test", "benchmark", "verify", "output of"])
            if (wants_exec or code_blocks) and code_blocks:
                code_to_exec = code_blocks[0].strip()
                try:
                    t0 = time.time()
                    res = subprocess.run([sys.executable, "-c", code_to_exec], capture_output=True, text=True, timeout=10)
                    duration_ms = (time.time() - t0) * 1000
                    exec_output = (res.stdout + ("\nSTDERR:\n" + res.stderr if res.stderr else "")).strip() or "[Execution completed with no stdout/stderr]"
                    status_str = "success" if res.returncode == 0 else "error"
                    telemetry_manager.add_tool_log("code_sandbox", code_to_exec[:60], status_str, duration_ms)
                    context_snippets.append(
                        f"--- CODE FORGE: LIVE RUNTIME EXECUTION RESULT ---\n"
                        f"Exit Code: {res.returncode}\n"
                        f"Output:\n{exec_output}\n"
                        f"Directive: Analyze the sandbox execution result above and integrate findings into your technical response."
                    )
                except subprocess.TimeoutExpired:
                    telemetry_manager.add_tool_log("code_sandbox", "Execution timed out", "timeout", 10000)
                    context_snippets.append("--- CODE FORGE: LIVE RUNTIME EXECUTION RESULT ---\n[Execution timed out after 10 seconds]")
                except Exception as e:
                    context_snippets.append(f"--- CODE FORGE: LIVE RUNTIME EXECUTION RESULT ---\n[Execution error: {e}]")

            context_snippets.append(
                "--- SPECIALIZATION DIRECTIVE: CODE FORGE ---\n"
                "You are CODE FORGE, JARVIS's elite software architect and engineering system.\n"
                "1. PRODUCTION CODE: Write clean, modular, robust code. Never use placeholders (no 'TODO', '...', or 'pass').\n"
                "2. STRICT TYPING & DOCS: Include comprehensive type annotations, input validation, and docstrings.\n"
                "3. COMPLEXITY ANALYSIS: Include Big-O Time Complexity and Space Complexity analysis for all algorithms.\n"
                "4. VERIFICATION SUITE: Provide a runnable test block or unit tests covering edge cases (empty inputs, boundaries, exceptions).\n"
                "5. ARCHITECTURAL RATIONALE: State the engineering trade-offs and rationale clearly."
            )

        # ─── MODE 2: CREATIVE CORE (CONCEPT STUDIO + Z-IMAGE-TURBO) ────────────
        elif op_mode == "creative":
            if not active_model or active_model == "llama2-uncensored:latest":
                active_model = config.ROUTING_CONFIG.get("creative", "openai/gpt-oss-120b")
            active_temperature = 0.75
            active_top_p = 0.95
            telemetry_manager.add_trace(f"[CREATIVE CORE] Concept Studio + Z-Image-Turbo engaged ({active_model})")

            # In Creative Core mode, every non-greeting prompt activates Z-Image-Turbo visual synthesis + Concept Studio direction
            trivial_greetings = {"hi", "hello", "hey", "yo", "hola", "namaste", "good morning", "good evening"}
            is_text_only_req = any(t in message_lower for t in ["no image", "without image", "text only", "don't generate an image"])
            should_synthesize_visual = (clean_msg.lower().strip() not in trivial_greetings) and not is_text_only_req

            if should_synthesize_visual:
                try:
                    t0 = time.time()
                    from core.image_engine import ImageGenerator
                    raw_visual_prompt = detected_image_prompt or clean_msg
                    clean_alt = re.sub(r'[\r\n\t]+', ' ', raw_visual_prompt).strip()
                    display_prompt = clean_alt[:110] + ("..." if len(clean_alt) > 110 else "")

                    banner_chunk = f"🎨 **Creative Core · Concept Studio + Z-Image-Turbo**: Synthesizing high-definition visual asset & studio direction...\n\n"
                    creative_prefix_chunks.append(banner_chunk)
                    yield banner_chunk

                    gen_res = ImageGenerator().generate(raw_visual_prompt)
                    duration_ms = (time.time() - t0) * 1000
                    if gen_res.get("status") == "success":
                        img_url = gen_res.get("url")
                        filename = gen_res.get("filename", "asset.png")
                        provider_info = gen_res.get("info", "Z-Image-Turbo")
                        aspect_str = gen_res.get("aspect", "1:1")
                        dims_str = f"{gen_res.get('width', 1024)}×{gen_res.get('height', 1024)}"
                        distilled_used = gen_res.get("distilled_prompt", "")

                        telemetry_manager.add_tool_log("image_gen", display_prompt[:80], "success", duration_ms)
                        img_block = (
                            f"![{display_prompt}]({img_url})\n\n"
                            f"**Engine**: `{provider_info}` · **Format**: `{aspect_str}` (`{dims_str}`) · **Archive**: `{filename}`\n\n"
                            f"---\n\n"
                        )
                        creative_prefix_chunks.append(img_block)
                        creative_img_rendered = True
                        yield img_block

                        context_snippets.append(
                            f"--- CREATIVE CORE: Z-IMAGE-TURBO SYNTHESIS ALREADY DISPLAYED ABOVE ---\n"
                            f"Rendered Image URL: {img_url}\n"
                            f"Format & Resolution: {aspect_str} ({dims_str})\n"
                            f"Distilled Diffusion Prompt Used: {distilled_used}\n"
                            f"CRITICAL DIRECTIVE: The synthesized image above is ALREADY rendered and visible at the top of the user's screen. "
                            f"Do NOT output any `![...](...)` markdown image tag or fake `/api/assets/images/...` link in your text. "
                            f"Provide a concise, authoritative **Concept Studio Art Direction Brief** directly below the image with:\n"
                            f"1. **Visual & Structural Architecture**: Key subject geometry, materials, surface finishes, and spatial composition.\n"
                            f"2. **Lighting & Optical Telemetry**: Studio/key illumination setup, color temperature, lens focal length, depth of field, and dynamic range.\n"
                            f"3. **Master Z-Image-Turbo / Flux Prompt Tags**: A copy-ready code block of positive diffusion tags for iterative studio refinement."
                        )
                except Exception as e:
                    logger.error(f"Creative Core image generation error: {e}")

            context_snippets.append(
                "--- SPECIALIZATION DIRECTIVE: CREATIVE CORE (CONCEPT STUDIO) ---\n"
                "You are CREATIVE CORE, JARVIS's elite Concept Studio Director and Industrial/Cinematic Visual Architect.\n"
                "1. PRECISION ART DIRECTION: Deliver crisp, structured visual direction grounded in real optical physics, industrial design, and cinematography.\n"
                "2. ZERO IMAGE LINK HALLUCINATION: Never invent or guess `/api/assets/images/gen_...` URLs.\n"
                "3. CONCISE STUDIO BREAKDOWN: Keep the Concept Studio breakdown sharp, well-formatted, and immediately actionable."
            )

        # ─── MODE 3: SECURITY SCAN ─────────────────────────────────────────────
        elif op_mode == "security":
            if not active_model or active_model == "llama2-uncensored:latest":
                active_model = config.ROUTING_CONFIG.get("security", "openai/gpt-oss-120b")
            active_temperature = 0.2
            telemetry_manager.add_trace(f"[SECURITY SCAN] Cyber Threat Intelligence & Vulnerability Auditor engaged ({active_model})")

            # Run live workstation security scan when host OS / Defender / Firewall / PC posture is mentioned
            host_sec_triggers = ["my pc", "my laptop", "my system", "workstation", "firewall", "defender", "malware", "host security", "startup", "processes", "system scan", "security status"]
            if any(k in message_lower for k in host_sec_triggers):
                try:
                    t0 = time.time()
                    from core.system_guardian import SystemGuardian
                    guardian = SystemGuardian()
                    sec_audit = guardian.audit_security_status(use_cache=True)
                    duration_ms = (time.time() - t0) * 1000
                    telemetry_manager.add_tool_log("security_guardian", "audit_security_status", "success", duration_ms)
                    context_snippets.append(
                        f"--- SECURITY SCAN: LIVE WORKSTATION AUDIT DATA ---\n"
                        f"{json.dumps(sec_audit, indent=2)}\n"
                        f"Directive: Present a professional Guardian Security Report summarizing firewall, protection, and workstation posture based on this telemetry."
                    )
                except Exception as e:
                    logger.error(f"System Guardian audit failed: {e}")

            context_snippets.append(
                "--- SPECIALIZATION DIRECTIVE: SECURITY SCAN ---\n"
                "You are SECURITY SCAN, JARVIS's Cyber Threat Intelligence and Vulnerability Assessment Auditor (Red Team / Blue Team).\n"
                "1. VULNERABILITY TRIAGE: Rigorously audit all targets for OWASP Top 10 (Injection, Broken Auth, SSRF, Deserialization), RCE, credential leaks, and permission escalation.\n"
                "2. STRUCTURED AUDIT REPORT FORMAT:\n"
                "   ### 🛡️ SECURITY AUDIT REPORT: [Target Component]\n"
                "   - **Overall Threat Level**: [CRITICAL | HIGH | MEDIUM | LOW | SECURE]\n"
                "   - **Vulnerabilities Identified**: (Severity, CWE/CVE, Attack Vector, Blast Radius)\n"
                "   - **Exploit Scenario**: (Proof of concept on how an adversary strikes)\n"
                "   - **Hardened Remediation**: (Exact code patch / diff to eliminate the flaw)\n"
                "   - **Defense-in-Depth Checklist**: (Headers, sanitization, rate-limiting, least-privilege)\n"
                "3. ZERO FALSE CONFIDENCE: Flag any unvalidated inputs, missing authentication, or plaintext secrets immediately."
            )

        # ─── MODE 4: INTEL RESEARCH ────────────────────────────────────────────
        elif op_mode in ["research", "intel", "web"]:
            if not active_model or active_model == "llama2-uncensored:latest":
                active_model = config.ROUTING_CONFIG.get("research", "openai/gpt-oss-120b")
            active_temperature = 0.3
            telemetry_manager.add_trace(f"[INTEL RESEARCH] Global reconnaissance and intelligence dossier engaged ({active_model})")

            # Autonomous Live Web Intelligence Gathering
            try:
                t0 = time.time()
                search_res = self.web_search.build_search_context(corrected_message, force=True, max_results=6)
                duration_ms = (time.time() - t0) * 1000
                telemetry_manager.add_tool_log("web_search", corrected_message[:60], "success" if search_res else "empty", duration_ms)
                if search_res:
                    context_snippets.append(
                        f"--- INTEL RESEARCH: LIVE SATELLITE & GROUND WEB INTELLIGENCE ---\n"
                        f"{search_res}\n"
                        f"--- END LIVE INTEL ---\n"
                        f"Directive: Synthesize this live data deeply into a verified intelligence dossier."
                    )
            except Exception as e:
                logger.error(f"Intel Research search error: {e}")

            context_snippets.append(
                "--- SPECIALIZATION DIRECTIVE: INTEL RESEARCH ---\n"
                "You are INTEL RESEARCH, JARVIS's Global Reconnaissance and Intelligence Synthesis Node.\n"
                "1. FACTUAL GROUNDING: Rely strictly on verified ground intelligence, dates, numbers, and cited sources from the live intel stream.\n"
                "2. CLASSIFIED BRIEFING FORMAT:\n"
                "   ### 🌐 CLASSIFIED INTEL BRIEFING: [Topic]\n"
                "   - **Executive Summary**: (Key findings in 3 bullet points)\n"
                "   - **Verified Ground Intelligence**: (Deep chronological or thematic breakdown)\n"
                "   - **Strategic Threat & Market Vectors**: (Second-order implications and risks)\n"
                "   - **Actionable Directives**: (Recommended strategic actions)\n"
                "   - **Intelligence Sources**: (Domains and source citations)\n"
                "3. OBJECTIVITY: Differentiate confirmed facts from probabilistic forecasting."
            )

        # ─── MODE 5: NEURAL CHAT (FLAGSHIP) ───────────────────────────────────
        else:
            active_model = active_model or config.ROUTING_CONFIG.get("chat", "qwen/qwen3.8-27b")
            active_temperature = 0.4
            telemetry_manager.set_active_mode("chat")
            telemetry_manager.add_trace(f"[NEURAL CHAT] Flagship Conversational Matrix Active via {active_model}")

            if not active_model:
                if any(k in message_lower for k in ["code", "python", "script", "java", "css", "html"]):
                    active_model = "qwen/qwen3.8-27b"
                elif any(k in message_lower for k in ["think", "reason", "complex", "plan", "strategy"]):
                    active_model = "deepseek/deepseek-chat"
                elif any(k in message_lower for k in ["analyze image", "what is in this", "see this"]):
                    active_model = "gemini-3.8-flash"

            # Direct web search fallback for chat
            if any(term in message_lower for term in ["search", "find", "latest", "news"]):
                search_res = self.web_search.build_search_context(corrected_message)
                if search_res:
                    context_snippets.append(search_res)

        # ─── Visual Entity & High-Res Photography Interceptor ─────────────────
        visual_dossier_data = None
        try:
            visual_dossier_data = self.web_search.get_entity_visual_dossier_data(corrected_message)
            if visual_dossier_data and visual_dossier_data.get("dossier_text"):
                logger.info("Visual Intelligence: Injected entity photographic dossier.")
                context_snippets.append(visual_dossier_data["dossier_text"])
        except Exception as e:
            logger.error(f"Visual entity dossier extraction error: {e}")

        # MCP Google Workspace Interceptor
        mcp_snippet = None
        if any(term in message_lower for term in ["email", "inbox", "mail"]):
            logger.info("Standard Mode: Fetching Gmail.")
            mcp_snippet = self._call_mcp_sync("google_workspace__read_unread_emails", {"max_results": 5})
        elif any(term in message_lower for term in ["calendar", "schedule", "meeting", "events", "agenda"]):
            logger.info("Standard Mode: Fetching Calendar.")
            mcp_snippet = self._call_mcp_sync("google_workspace__get_upcoming_events", {"max_results": 5})
        elif any(term in message_lower for term in ["drive", "document", "doc"]):
            logger.info("Standard Mode: Fetching Drive.")
            query = corrected_message.replace("search drive for", "").replace("find in drive", "").strip()
            if query:
                mcp_snippet = self._call_mcp_sync("google_workspace__search_drive", {"query": query})
        
        if mcp_snippet:
            context_snippets.append(f"--- LIVE GOOGLE WORKSPACE DATA ---\n{mcp_snippet}\n(Only mention the details provided above, do not invent emails or events.)")

        # --- Live Host System Status & Diagnostics Interceptor ---
        status_triggers = ["system status", "report system status", "diagnostics", "system health", "vitals", "system report", "server status", "hardware status", "status of jarvis"]
        if any(trigger in message_lower for trigger in status_triggers):
            try:
                import psutil, threading
                cpu_load = psutil.cpu_percent(interval=0.1)
                ram_mem = psutil.virtual_memory()
                net_io = psutil.net_io_counters()
                uptime_val = "Active"
                try:
                    import app
                    uptime_secs = int(time.time() - getattr(app, "SERVER_START_TIME", time.time()))
                    uptime_val = f"{uptime_secs // 3600}h {(uptime_secs % 3600) // 60}m"
                except Exception:
                    pass

                current_time_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

                context_snippets.append(
                    f"--- AUTHENTIC LIVE SYSTEM TELEMETRY (REAL-TIME SENSORS) ---\n"
                    f"Timestamp: {current_time_str}\n"
                    f"Environment: {'Render Cloud Linux' if os.getenv('RENDER') else 'Local Workstation Node'}\n"
                    f"Current Process Uptime: {uptime_val}\n"
                    f"Historical Availability: NOT MEASURED (Subject to standard host lifecycles)\n"
                    f"Current CPU Load: {cpu_load}%\n"
                    f"Memory Pool (RAM): {ram_mem.used / (1024**3):.1f} GB allocated / {ram_mem.total / (1024**3):.1f} GB ({ram_mem.percent}% utilization)\n"
                    f"Active Python Threads: {threading.active_count()}\n"
                    f"Network Outbound: {net_io.bytes_sent / (1024**2):.1f} MB\n"
                    f"Security Perimeter: Command execution isolation: NOT ESTABLISHED | Prompt-injection guard: DESIGNED\n"
                    f"Directive: You must cite the exact measurements and timestamp above (e.g., 'According to runtime telemetry collected at {current_time_str}, current CPU is {cpu_load}%...'). Do NOT invent fictional percentages, and do not make unverified claims about 24/7 perpetual uptime or zero-trust sandboxing."
                )
            except Exception as e:
                logger.error(f"Live telemetry injection error: {e}")

        # --- Conversation Transcript / Source Export Interceptor ---
        message_lower = corrected_message.lower()
        export_triggers = [
            "give me my conversation source file",
            "give me the conversation source",
            "give me conversation source",
            "conversation source file",
            "export conversation",
            "export my conversation",
            "export transcript",
            "download transcript",
            "export chat log"
        ]
        if any(trigger in message_lower for trigger in export_triggers):
            try:
                req_fmt = "jsonl" if any(k in message_lower for k in ["source", "jsonl"]) else "markdown"
                export_path = self.export_conversation(conv_id, format=req_fmt)
                export_abs = os.path.abspath(export_path)
                logger.info(f"Auto-Exported conversation {conv_id} to {export_abs}")
                context_snippets.append(
                    f"--- CONVERSATION EXPORT READY ---\n"
                    f"The user requested their conversation source/transcript file.\n"
                    f"Export Format: {req_fmt}\n"
                    f"Export File Path: {export_abs}\n"
                    f"Web/API Download Route: /api/conversations/{conv_id}/export?format={req_fmt}\n"
                    f"Directive: Confirm to the user that their conversation source file has been generated and provide the file path clearly."
                )
            except Exception as e:
                logger.error(f"Auto-export error for conversation {conv_id}: {e}")

        # --- File & Multimodal Image Attachment Context Injection ---
        resolved_img_path = kwargs.get("image_path")
        if not resolved_img_path and file_context:
            # Check if filename is mentioned in file_context
            match_file = re.search(r'up_[a-f0-9]+_[^\s\n\r]+', str(file_context))
            if match_file:
                candidate_p = os.path.join(config.UPLOAD_DIR, match_file.group(0))
                if os.path.exists(candidate_p) and any(candidate_p.lower().endswith(e) for e in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]):
                    resolved_img_path = candidate_p

        # If we have an image path and file_context does not already contain deep vision analysis, run vision model
        if resolved_img_path and os.path.exists(resolved_img_path):
            if "VISUAL RECOGNITION & OCR ANALYSIS" not in str(file_context):
                try:
                    logger.info(f"ChatEngine: Executing on-demand vision analysis for {resolved_img_path}")
                    v_prompt = (
                        f"Analyze this image in the context of the user's message: '{corrected_message}'. "
                        "Identify subjects, layout, diagrams, extract any visible text/code/errors (OCR), and provide clear findings."
                    )
                    vision_result = self.model.generate_vision(v_prompt, resolved_img_path)
                    if vision_result and not str(vision_result).startswith("Vision processing failed"):
                        context_snippets.append(
                            f"--- DIRECT MULTIMODAL VISION OBSERVATION ---\n"
                            f"Image: {os.path.basename(resolved_img_path)}\n"
                            f"{vision_result}\n"
                            f"--- END VISION OBSERVATION ---\n"
                            f"Directive: You have directly seen this image through your vision sensors. Answer the user's inquiry accurately based on these visual details."
                        )
                except Exception as e:
                    logger.warning(f"ChatEngine direct vision analysis failed: {e}")

        if file_context and str(file_context).strip():
            logger.info("ChatEngine: Ingesting attached file context into active reasoning pipeline.")
            context_snippets.append(
                f"--- USER ATTACHED FILE CONTEXT ---\n"
                f"{str(file_context).strip()}\n"
                f"--- END ATTACHED FILE CONTEXT ---\n"
                f"Directive: The user has attached a file/image. Prioritize analyzing and responding based on its content."
            )

        # --- Memory Injection (Upgrade 1) ---
        # 1. RAG Long-term Memory
        rag_context = self.knowledge.build_context_prompt(corrected_message)
        if rag_context:
            context_snippets.append(rag_context)

        # 2. Omega Cognitive Memory Engine Sync (Session-Aware)
        try:
            omega_context = self.omega_memory.process_input(corrected_message, conv_id=conv_id)
            if omega_context:
                context_snippets.append(omega_context)
        except Exception as e:
            logger.error(f"Omega Memory processing failed: {e}")
            
        # 3. Extract and Inject User Preferences (Short/Long term)
        if user and hasattr(user, 'preferences'):
            user.preferences = self.memory.extract_preferences(corrected_message, user.preferences or {})
            memory_snippet = self.memory.build_memory_snippet(user.preferences)
            if memory_snippet:
                context_snippets.append(memory_snippet)
                
        # 4. Conversation Summarization
        if len(conv.get("messages", [])) > 15:
            if "summary" in conv:
                sum_text = conv["summary"]
                if not self.is_refusal(sum_text) and "refused to comply" not in sum_text.lower():
                    context_snippets.append(f"--- PREVIOUS CONVERSATION SUMMARY ---\n{sum_text}\n-----------------------------------\n")
                
            # Async summary update every 5 messages
            if len(conv.get("messages", [])) % 5 == 0:
                def update_summary():
                    try:
                        msgs = conv["messages"][:-10]
                        text = "Summarize the key context and facts established in this conversation so far:\n" + "\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in msgs[-20:]])
                        new_summary = self.model.generate([{"role": "user", "content": text}], system_prompt="You are a precise memory summarizer. Provide concise bullet points.", model=config.ROUTING_CONFIG.get("fast", "llama-3.1-8b-instant"))
                        if new_summary:
                            conv["summary"] = new_summary
                            self._save_conversation(conv_id)
                    except Exception as e:
                        logger.error(f"Summary update failed: {e}")
                import threading
                threading.Thread(target=update_summary, daemon=True).start()

        # 3. Final Formulation
        system_prompt = config.SYSTEM_PROMPT.format(current_date=datetime.now().strftime("%B %d, %Y"))
        if config.UNCENSORED_MODE and getattr(config, "STARK_RAW_PROTOCOL", ""):
            system_prompt += f"\n\n{config.STARK_RAW_PROTOCOL}"
        
        # Personality Injection
        if user and hasattr(user, 'preferences'):
            active_personality = (user.preferences or {}).get("personality", "normal")
            personality_prompt = config.PERSONALITY_PROMPTS.get(active_personality, config.PERSONALITY_PROMPTS["normal"])
            system_prompt += f"\n\n# ACTIVE PERSONALITY: {active_personality}\n{personality_prompt}"

        if config.AGENT_THINKING_BLOCK and getattr(config, "THINKING_DIRECTIVE", ""):
            system_prompt += f"\n\n{config.THINKING_DIRECTIVE}"

        if context_snippets:
            system_prompt += "\n--- INTEL SUMMARY ---\n" + "\n".join([str(s) for s in context_snippets if s])

        # Build history (keep recent messages, capped by character budget for token headroom)
        raw_history = []
        for m in conv.get("messages", [])[-12:]:
            c_text = (m.get("content") or "").strip()
            # Do not inject previous error banners, empty items, or canned refusal phrases into model context
            if c_text and not c_text.startswith("⚠️") and not self.is_refusal(c_text):
                if creative_img_rendered:
                    # Strip prior markdown image embeds from LLM prompt context so the model does not mimic/hallucinate fake asset URLs
                    c_text = re.sub(r"!\[[^\]]*\]\(/api/assets/images/[^)]+\)\s*", "", c_text).strip()
                if c_text:
                    raw_history.append({"role": m.get("role", "user"), "content": c_text})

        # Cap total history characters to 12,000 to prevent provider 413 payload / rate limit overflows
        history = []
        running_chars = 0
        for m in reversed(raw_history):
            c_len = len(m.get("content", ""))
            if running_chars + c_len > 12000 and len(history) >= 2:
                break
            history.insert(0, m)
            running_chars += c_len
        
        user_turn_text = (corrected_message or "").strip() or "Hello"
        model_user_turn = self.normalize_esoteric_query(user_turn_text)
        history.append({"role": "user", "content": model_user_turn})
        
        # Stream response with real-time thinking block suppression
        full_response = list(creative_prefix_chunks)

        # ─── Guaranteed Visual Intelligence Delivery ───
        # If verified original photographs were found, yield the primary portrait immediately!
        if visual_dossier_data and visual_dossier_data.get("images") and not creative_img_rendered:
            primary_img = visual_dossier_data["images"][0]
            img_card = f"![{primary_img['title']}]({primary_img['url']})\n\n"
            full_response.append(img_card)
            yield img_card

        # Helper to execute stream with custom history and model
        def execute_stream(target_model_name, prompt_content):
            req_history = list(history[:-1]) + [{"role": "user", "content": prompt_content}]
            return self.model.generate_stream(
                req_history, 
                system_prompt, 
                user_tier=getattr(user, 'tier', 'free'), 
                model_override=target_model_name,
                temperature=active_temperature,
                top_p=active_top_p
            )

        def stream_with_interception(stream_gen):
            buffered = []
            buf_str = ""
            for chunk in stream_gen:
                if not chunk:
                    continue
                buffered.append(chunk)
                buf_str += chunk
                if len(buf_str) >= 90:
                    break
            
            if self.is_refusal(buf_str):
                return True, buf_str, None
            
            def pass_through():
                for b in buffered:
                    yield b
                for chunk in stream_gen:
                    yield chunk

            return False, buf_str, pass_through()

        raw_stream = execute_stream(active_model, model_user_turn)
        filt_stream = self._filter_thinking_stream(raw_stream)
        is_refused, ref_text, valid_gen = stream_with_interception(filt_stream)

        if is_refused:
            logger.warning(f"Refusal Interceptor: Intercepted refusal '{ref_text.strip()}'. Auto-healing with failover chain...")
            failover_candidates = ["meta-llama/llama-3.3-70b-instruct", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
            healed = False
            for fb_model in failover_candidates:
                if fb_model == active_model:
                    continue
                try:
                    logger.info(f"Refusal Interceptor: Failover attempt using node '{fb_model}'...")
                    fb_raw = execute_stream(fb_model, model_user_turn)
                    fb_filt = self._filter_thinking_stream(fb_raw)
                    fb_refused, fb_text, fb_gen = stream_with_interception(fb_filt)
                    if not fb_refused and fb_gen:
                        healed = True
                        for chunk in fb_gen:
                            full_response.append(chunk)
                            yield chunk
                        break
                except Exception as fb_err:
                    logger.warning(f"Refusal Interceptor failover node '{fb_model}' error: {fb_err}")
                    continue

            if not healed:
                fallback_intel = (
                    "**Historical Grimoires & Solomonic Demonology (Ars Goetia)**\n\n"
                    "In Western Renaissance esotericism (*The Lesser Key of Solomon*, 17th c.), "
                    "traditional grimoires document 72 Goetic spirits, categorized by hierarchical rank "
                    "(Kings, Dukes, Princes, Marquises, Counts, Presidents) along with their corresponding symbolic seals and protective pentacles.\n\n"
                    "### Core Solomonic Geometry\n"
                    "- **The Magic Circle:** Inscribed with divine names to serve as the practitioner's impenetrable boundary.\n"
                    "- **The Triangle of Arte (Manifestation):** Positioned outside the circle where the spirit's sigil is placed for bound evocation.\n"
                    "- **The Hexagram & Pentagram of Solomon:** Worn as parchment or metallic lamens for spiritual defense.\n"
                    "- **Goetic Sigils:** Unique geometric monograms associated with each spirit (e.g., Bael, Agares, Vassago, Asmodeus, Belial) historically drawn on parchment or engraved in designated metals."
                )
                full_response.append(fallback_intel)
                yield fallback_intel
        else:
            for chunk in valid_gen:
                full_response.append(chunk)
                yield chunk

        # 4. Neural After-Action Process
        assistant_message = "".join(full_response)
        assistant_message = self.clean_response(assistant_message)

        # Heal any LLM-hallucinated Markdown image tags so persisted history always points to a real synthesized image
        if "![" in assistant_message and "](" in assistant_message:
            def _heal_md_img(match):
                alt_txt = (match.group(1) or "").strip()
                img_url = (match.group(2) or "").strip()
                if "wikimedia.org" in img_url or img_url.startswith("data:"):
                    return match.group(0)
                if img_url.startswith("/api/assets/images/"):
                    fname = os.path.basename(img_url.split("?")[0])
                    if os.path.isfile(os.path.join(config.IMAGE_GEN_DIR, fname)):
                        return match.group(0)
                    if creative_img_rendered:
                        # An authentic Creative Core image was already rendered at the top; strip any duplicate hallucinated tag
                        return ""
                try:
                    from core.image_engine import ImageGenerator
                    synth = ImageGenerator().generate(alt_txt or message)
                    if synth.get("status") == "success" and synth.get("url"):
                        return f"![{alt_txt or 'Synthesized Visualization'}]({synth['url']})"
                except Exception as heal_err:
                    logger.warning(f"Post-stream Markdown image heal error: {heal_err}")
                return match.group(0)

            assistant_message = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _heal_md_img, assistant_message)
        
        # Guard: Never persist a refusal into conversation history to prevent future context poisoning
        if not self.is_refusal(assistant_message):
            now_iso = datetime.now(timezone.utc).isoformat()
            conv["messages"].append({"role": "user", "content": message, "timestamp": now_iso})
            conv["messages"].append({"role": "assistant", "content": assistant_message, "timestamp": now_iso})
            self._save_conversation(conv_id)

        try:
            self.omega_memory.update_session("assistant", assistant_message, conv_id=conv_id)
            self.omega_memory._save_memory(self.omega_memory.memory)
        except Exception as e:
            logger.error(f"Omega Memory assistant session update failed: {e}")

    def new_conversation(self, title: str = "", conv_id: Optional[str] = None) -> dict:
        conv_id = conv_id or str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        conversation = {"id": conv_id, "title": title or "New Conversation", "created": now, "updated": now, "messages": []}
        self._conversations[conv_id] = conversation
        self._current_conversation_id = conv_id
        self._save_conversation(conv_id)
        try:
            self.omega_memory.start_conversation(conv_id)
        except Exception as e:
            logger.error(f"Omega Memory start_conversation failed: {e}")
        return {"id": conv_id, "title": conversation["title"]}

    def list_conversations(self, user_id: int) -> list:
        result = []
        for cid, conv in self._conversations.items():
            result.append({
                "id": cid,
                "title": conv.get("title", "Thread"),
                "updated_at": conv.get("updated", datetime.now(timezone.utc).isoformat()),
                "message_count": len(conv.get("messages", []))
            })
        return sorted(result, key=lambda x: x["updated_at"], reverse=True)

    def get_conversation(self, conv_id: str) -> dict:
        return self._conversations.get(conv_id, {})

    def delete_conversation(self, conv_id: str):
        if conv_id in self._conversations:
            del self._conversations[conv_id]
        filepath = os.path.join(config.CONVERSATION_DIR, f"{conv_id}.json")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error(f"Failed to delete {filepath}: {e}")

    def _save_conversation(self, conv_id: str):
        if conv_id in self._conversations:
            filepath = os.path.join(config.CONVERSATION_DIR, f"{conv_id}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._conversations[conv_id], f, indent=2)

    def _load_conversations(self):
        if not os.path.exists(config.CONVERSATION_DIR): return
        for filename in os.listdir(config.CONVERSATION_DIR):
            if filename.endswith(".json"):
                conv_id = filename[:-5]
                filepath = os.path.join(config.CONVERSATION_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._conversations[conv_id] = json.load(f)
                except: pass

    def export_conversation(self, conv_id: Optional[str] = None, format: str = "jsonl") -> str:
        """Export a conversation as json, jsonl, or markdown."""
        conv_id = conv_id or self._current_conversation_id
        conv = self._conversations.get(conv_id)
        if not conv:
            raise ValueError(f"Conversation '{conv_id}' not found.")

        os.makedirs(self.exports_dir, exist_ok=True)
        fmt = (format or "jsonl").lower().strip()

        if fmt == "json":
            filepath = os.path.join(self.exports_dir, f"{conv_id}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(conv, f, indent=2)
            return filepath

        elif fmt in ("markdown", "md"):
            filepath = os.path.join(self.exports_dir, f"{conv_id}.md")
            lines = [
                f"# Conversation Transcript: {conv.get('title', 'Untitled')}",
                f"**ID:** `{conv.get('id', conv_id)}`  ",
                f"**Created:** {conv.get('created', 'N/A')}  ",
                f"**Updated:** {conv.get('updated', 'N/A')}  \n",
                "---",
            ]
            for msg in conv.get("messages", []):
                role = msg.get("role", "unknown").capitalize()
                ts = msg.get("timestamp", "")
                content = msg.get("content", "")
                lines.append(f"\n### {role} ({ts})\n{content}\n")
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return filepath

        elif fmt == "jsonl":
            filepath = os.path.join(self.exports_dir, f"{conv_id}.jsonl")
            with open(filepath, "w", encoding="utf-8") as f:
                header = {
                    "type": "conversation_metadata",
                    "id": conv.get("id", conv_id),
                    "title": conv.get("title", ""),
                    "created": conv.get("created"),
                    "updated": conv.get("updated"),
                    "message_count": len(conv.get("messages", []))
                }
                f.write(json.dumps(header) + "\n")
                for msg in conv.get("messages", []):
                    record = {
                        "conversation_id": conv_id,
                        "role": msg.get("role"),
                        "content": msg.get("content"),
                        "timestamp": msg.get("timestamp")
                    }
                    f.write(json.dumps(record) + "\n")
            return filepath
        else:
            raise ValueError(f"Unsupported format '{format}'. Supported formats: 'json', 'jsonl', 'markdown'.")

