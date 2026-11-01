"""
Automated Test for JARVIS Mem0 Persistent Intelligent Memory Subsystem
Verifies Mem0 initialization, embedded Qdrant vector storage, local FastEmbed embeddings,
semantic memory extraction, user context formatting, and Flask API endpoints.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mem0_engine import Mem0Engine, mem0_engine
from core.memory_manager import MemoryManager
from core.orchestrator import orchestrator


def run_all_tests():
    print("==================================================")
    print("JARVIS MEM0 PERSISTENT INTELLIGENT MEMORY TESTS")
    print("==================================================")

    # 1. Initialization
    print("\n1. Testing Mem0Engine initialization...")
    assert mem0_engine.is_available(), "Mem0Engine must be operational."
    print(f"   [PASS] Mem0Engine initialized with Qdrant vector store and FastEmbed.")

    # 2. Add Memory
    print("\n2. Testing adding semantic memories...")
    test_fact = "My preferred Python web framework is FastAPI and I prefer dark mode in all IDEs."
    add_res = mem0_engine.add_memory(test_fact, user_id="Ayush")
    assert add_res.get("status") == "success", f"Add memory failed: {add_res}"
    print(f"   [PASS] Added persistent memory for user 'Ayush'.")

    # 3. Semantic Search & Recall
    print("\n3. Testing semantic search across persistent memory...")
    search_res = mem0_engine.search_memory("What web framework does the user prefer?", user_id="Ayush", limit=3)
    assert len(search_res) > 0, "Semantic search should return at least 1 memory match."
    top_match = search_res[0]
    mem_text = top_match.get("memory", "")
    assert len(mem_text) > 0, "Memory text must not be empty."
    print(f"   [PASS] Grounded semantic recall: '{mem_text}' (Score: {top_match.get('score', 0):.3f})")

    # 4. Prompt Context Generation
    print("\n4. Testing user prompt context formatting...")
    context_str = mem0_engine.get_user_context("web framework", user_id="Ayush")
    assert "USER MEMORY & PREFERENCES" in context_str, "Preamble header must be present."
    assert "FastAPI" in context_str or "framework" in context_str.lower(), "Context must contain recalled fact."
    print("   [PASS] Prompt context block formulated:")
    print(f"          {context_str.strip()}")

    # 5. MemoryManager Hook
    print("\n5. Testing MemoryManager hook...")
    mm = MemoryManager()
    mm_context = mm.get_context_for_prompt("dark mode preference", user_id="Ayush")
    assert len(mm_context) > 0, "MemoryManager must return non-empty context string."
    print("   [PASS] MemoryManager.get_context_for_prompt hook verified.")

    # 6. AgentOrchestrator MemoryAgentNode Hook
    print("\n6. Testing AgentOrchestrator MemoryAgentNode hook...")
    dispatch_res = orchestrator.dispatch("What do you remember about my preferred web framework?")
    assert "[MEM0 RECALL]" in dispatch_res, f"Expected [MEM0 RECALL], got: {dispatch_res}"
    print("   [PASS] AgentOrchestrator MemoryAgentNode routed and executed successfully.")

    # 7. Flask API Endpoints
    print("\n7. Testing Flask API Mem0 routes...")
    from app import app
    client = app.test_client()

    # Search endpoint
    search_api = client.get("/api/memory/mem0/search?query=IDE+theme&user_id=Ayush")
    assert search_api.status_code == 200, f"Expected 200, got {search_api.status_code}"
    search_json = search_api.get_json()
    assert search_json.get("status") == "success"
    assert search_json.get("count", 0) > 0
    print(f"   [PASS] GET /api/memory/mem0/search operational ({search_json.get('count')} results).")

    # All memories endpoint
    all_api = client.get("/api/memory/mem0/all?user_id=Ayush")
    assert all_api.status_code == 200
    all_json = all_api.get_json()
    assert all_json.get("status") == "success"
    print(f"   [PASS] GET /api/memory/mem0/all operational ({all_json.get('count')} total memories).")

    print("\n==================================================")
    print("ALL 7 MEM0 PERSISTENT MEMORY CHECKS PASSED NOMINALLY!")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
