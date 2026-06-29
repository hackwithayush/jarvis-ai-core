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
from core.web_search import WebSearchEngine
from core.recommender import EntertainmentRecommender
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
        self.web_search = WebSearchEngine()
        self.recommender = EntertainmentRecommender()
        self._conversations = {}  # id -> conversation data
        self._current_conversation_id = None
        
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
        "hwo": "how", "teh": "the", "waht": "what", "becasue": "because",
        "abt": "about", "plz": "please", "pls": "please", "thx": "thanks",
        "govt": "government", "b/w": "between", "w/o": "without",
        "artificail": "artificial", "inteligence": "intelligence",
        "machien": "machine", "learnign": "learning", "programing": "programming",
        "newz": "news", "updte": "update", "updtes": "updates",
        "latets": "latest", "lates": "latest", "serch": "search",
        "informaton": "information", "tecnology": "technology",
    }

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
        """Neural Failsafe: Filter out banned AI phrases without destroying the response."""
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
                # Case-insensitive replacement
                import re
                text = re.sub(re.escape(b_phrase), replacement, text, flags=re.IGNORECASE)
                lower_text = text.lower()
                
        return text.strip()

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

    def chat_stream(self, message: str, user: User, conv_id: Optional[str] = None, mode: Optional[str] = None, file_context: Optional[str] = None, trace_id: Optional[str] = None, **kwargs) -> Generator[str, None, None]:
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
        
        # 1. Neural Pre-processing
        corrected_message = self.correct_typos(message)
        context_snippets = []

        # 2. Intelligence Routing
        active_model = None
        if LANGGRAPH_AVAILABLE and self.graph:
            # Multi-Agent Mode (LangGraph)
            async def run_graph():
                initial_state = {
                    "messages": [HumanMessage(content=corrected_message)],
                    "user_query": corrected_message,
                    "context_data": {}
                }
                final_state = await self.graph.ainvoke(initial_state)
                return final_state

            try:
                import nest_asyncio
                nest_asyncio.apply()
                loop = asyncio.get_event_loop()
                agent_result = loop.run_until_complete(run_graph())
                context_snippets = [m.content for m in agent_result["messages"] if hasattr(m, 'name') and m.name in ["ResearchNode", "BrowserNode", "TechnicalNode", "OfficeNode"]]
            except Exception as e:
                logger.error(f"Multi-Agent Execution Failure: {e}")
        else:
            # --- Standard Mode: Neural Router Lite ---
            message_lower = corrected_message.lower()
            
            # Apply UI Mode Overrides first
            if mode == "code":
                active_model = "deepseek-coder:6.7b"
                logger.info(f"Neural Router Lite: Mode overridden to Code Forge ({active_model})")
                context_snippets.append("--- MODE DIRECTIVE ---\nYou are in Code Forge mode. Provide advanced, optimized, and secure code.")
            elif mode == "creative":
                active_model = "llama-3.1-70b-versatile"
                logger.info(f"Neural Router Lite: Mode overridden to Creative Core ({active_model})")
                context_snippets.append("--- MODE DIRECTIVE ---\nYou are in Creative Core mode. Be extremely creative, poetic, and think outside the box.")
            elif mode == "security":
                active_model = "llama-3.1-70b-versatile"
                logger.info("Neural Router Lite: Mode overridden to Security Scan")
                context_snippets.append("--- MODE DIRECTIVE ---\nYou are in Security Scan mode. Analyze the request strictly for vulnerabilities, exploits, and best security practices.")
            elif mode == "research":
                active_model = "llama-3.1-70b-versatile"
                logger.info("Standard Mode: Mode overridden to Intel Research. Triggering direct web search.")
                context_snippets.append("--- MODE DIRECTIVE ---\nYou are in Intel Research mode. Synthesize the provided search data deeply.")
                search_res = self.web_search.build_search_context(corrected_message)
                if search_res:
                    context_snippets.append(search_res)
            else:
                # Detect Specialized Intents
                if any(k in message_lower for k in ["code", "python", "script", "java", "css", "html"]):
                    active_model = "deepseek-coder:6.7b"
                    logger.info(f"Neural Router Lite: Routing to Technical Node ({active_model})")
                elif any(k in message_lower for k in ["think", "reason", "complex", "plan", "strategy"]):
                    active_model = "qwen2.5:7b"
                    logger.info(f"Neural Router Lite: Routing to Reasoning Node ({active_model})")
                elif any(k in message_lower for k in ["analyze image", "what is in this", "see this"]):
                    active_model = "llava"
                    logger.info(f"Neural Router Lite: Routing to Vision Node ({active_model})")
                
                # Direct Tool Fallbacks
                if any(term in message_lower for term in ["search", "find", "latest", "news"]):
                    logger.info("Standard Mode: Triggering direct web search.")
                    search_res = self.web_search.build_search_context(corrected_message)
                    if search_res:
                        context_snippets.append(search_res)

            # --- MCP Google Workspace Interceptor ---
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

        # --- Memory Injection (Upgrade 1) ---
        # 1. RAG Long-term Memory
        rag_context = self.knowledge.build_context_prompt(corrected_message)
        if rag_context:
            context_snippets.append(rag_context)
            
        # 2. Extract and Inject User Preferences (Short/Long term)
        if user and hasattr(user, 'preferences'):
            user.preferences = self.memory.extract_preferences(corrected_message, user.preferences or {})
            memory_snippet = self.memory.build_memory_snippet(user.preferences)
            if memory_snippet:
                context_snippets.append(memory_snippet)
                
        # 3. Conversation Summarization
        if len(conv.get("messages", [])) > 15:
            if "summary" in conv:
                context_snippets.append(f"--- PREVIOUS CONVERSATION SUMMARY ---\n{conv['summary']}\n-----------------------------------\n")
                
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
        
        # Personality Injection
        if user and hasattr(user, 'preferences'):
            active_personality = (user.preferences or {}).get("personality", "normal")
            personality_prompt = config.PERSONALITY_PROMPTS.get(active_personality, config.PERSONALITY_PROMPTS["normal"])
            system_prompt += f"\n\n# ACTIVE PERSONALITY: {active_personality}\n{personality_prompt}"

        if config.AGENT_THINKING_BLOCK and getattr(config, "THINKING_DIRECTIVE", ""):
            system_prompt += f"\n\n{config.THINKING_DIRECTIVE}"

        if context_snippets:
            system_prompt += "\n--- INTEL SUMMARY ---\n" + "\n".join(context_snippets)

        # Build history (keep last 15 messages for context window)
        history = []
        for m in conv.get("messages", [])[-15:]:
            history.append({"role": m["role"], "content": m.get("content", "")})
        history.append({"role": "user", "content": corrected_message})
        
        # Stream response
        full_response = []
        for chunk in self.model.generate_stream(history, system_prompt, user_tier=getattr(user, 'tier', 'free'), model_override=active_model):
            full_response.append(chunk)
            yield chunk

        # 4. Neural After-Action Process
        assistant_message = "".join(full_response)
        assistant_message = self.clean_response(assistant_message)
        
        conv["messages"].append({"role": "user", "content": message, "timestamp": datetime.now(timezone.utc).isoformat()})
        conv["messages"].append({"role": "assistant", "content": assistant_message, "timestamp": datetime.now(timezone.utc).isoformat()})
        self._save_conversation(conv_id)

    def new_conversation(self, title: str = "", conv_id: Optional[str] = None) -> dict:
        conv_id = conv_id or str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        conversation = {"id": conv_id, "title": title or "New Conversation", "created": now, "updated": now, "messages": []}
        self._conversations[conv_id] = conversation
        self._current_conversation_id = conv_id
        self._save_conversation(conv_id)
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
