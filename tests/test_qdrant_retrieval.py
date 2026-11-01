"""
Automated Test for JARVIS Qdrant Semantic Knowledge Retrieval Engine
Verifies local embedded Qdrant initialization, FastEmbed dense vector generation,
document chunking and indexing, multi-collection semantic search, RAG context generation,
and Flask REST API endpoints.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.qdrant_engine import QdrantEngine, qdrant_engine


def run_all_tests():
    print("==================================================")
    print("JARVIS QDRANT SEMANTIC KNOWLEDGE RETRIEVAL TESTS")
    print("==================================================")

    # 1. Initialization
    print("\n1. Testing QdrantEngine initialization...")
    assert qdrant_engine.is_available(), "QdrantEngine must be operational."
    assert qdrant_engine.client is not None, "QdrantClient must exist."
    assert qdrant_engine.embed_model is not None, "FastEmbed model must exist."
    print("   [PASS] QdrantEngine initialized with local FastEmbed (384d) and storage.")

    # 2. Embedding vector generation
    print("\n2. Testing dense vector embedding generation...")
    vec = qdrant_engine.embed_text("Autonomous AI workstation operating system")
    assert len(vec) == 384, f"Expected 384d vector, got {len(vec)}"
    print(f"   [PASS] Generated 384-dimensional dense vector.")

    # 3. Document Indexing
    print("\n3. Testing document chunking and indexing...")
    doc_content = (
        "Project Stark Omega Architecture: Jarvis uses LangGraph for stateful agent orchestration. "
        "Mem0 provides persistent episodic memory across sessions using local Qdrant vectors. "
        "Microsoft OmniParser performs pixel-accurate visual UI grounding and coordinate targeting on Windows displays. "
        "Silero VAD enables low-latency conversational barge-in, allowing the user to interrupt mid-speech."
    )
    idx_res = qdrant_engine.index_document(
        content=doc_content,
        title="Stark Omega Specifications",
        category="architecture",
        source="internal_docs"
    )
    assert idx_res.get("status") == "success", f"Indexing failed: {idx_res}"
    assert idx_res.get("chunks_indexed", 0) > 0, "At least 1 chunk must be indexed."
    print(f"   [PASS] Indexed '{idx_res['title']}' ({idx_res['chunks_indexed']} chunks).")

    # 4. Semantic Search
    print("\n4. Testing semantic search across indexed knowledge...")
    hits = qdrant_engine.search("How does Jarvis handle user interruptions during speech?", limit=3)
    assert len(hits) > 0, "Semantic search must return matching results."
    top_hit = hits[0]
    assert "Silero VAD" in top_hit["text"] or "barge-in" in top_hit["text"].lower(), "Top hit must match interruption concept."
    print(f"   [PASS] Top semantic hit: '{top_hit['title']}' (Score: {top_hit['score']:.3f})")
    print(f"          Snippet: {top_hit['text'][:90]}...")

    # 5. RAG Prompt Context Generation
    print("\n5. Testing RAG context formatting for LLM prompts...")
    rag_context = qdrant_engine.get_rag_context("visual UI grounding", limit=2)
    assert "RELEVANT KNOWLEDGE BASE CONTEXT" in rag_context, "RAG header must exist."
    assert "OmniParser" in rag_context or "visual" in rag_context.lower(), "Context must contain relevant snippet."
    print("   [PASS] Formatted RAG context block generated:")
    print(f"          {rag_context.strip()[:140]}...")

    # 6. Workspace Codebase Indexing
    print("\n6. Testing workspace code indexing...")
    ws_res = qdrant_engine.index_workspace(os.getcwd(), max_files=10)
    assert ws_res.get("status") == "success", f"Workspace indexing failed: {ws_res}"
    assert ws_res.get("files_indexed", 0) > 0, "Must index at least 1 file."
    print(f"   [PASS] Indexed {ws_res['files_indexed']} workspace source files ({ws_res['total_chunks']} chunks).")

    # 7. Flask API Endpoints
    print("\n7. Testing Flask API Qdrant routes...")
    from app import app
    client = app.test_client()

    # Stats endpoint
    stats_resp = client.get("/api/knowledge/qdrant/stats")
    assert stats_resp.status_code == 200, f"Expected 200, got {stats_resp.status_code}"
    stats_data = stats_resp.get_json()
    assert stats_data.get("status") == "online"
    print(f"   [PASS] GET /api/knowledge/qdrant/stats operational (Status: {stats_data['status']}).")

    # Search endpoint
    search_resp = client.post("/api/knowledge/qdrant/search", json={
        "query": "LangGraph stateful orchestration",
        "limit": 2
    })
    assert search_resp.status_code == 200
    search_data = search_resp.get_json()
    assert search_data.get("status") == "success"
    assert search_data.get("count", 0) > 0
    print(f"   [PASS] POST /api/knowledge/qdrant/search operational ({search_data['count']} hits).")

    print("\n==================================================")
    print("ALL 7 QDRANT KNOWLEDGE RETRIEVAL CHECKS PASSED NOMINALLY!")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
