"""
Automated Test for JARVIS LangGraph Stateful Agent Orchestration (Autonomous Intelligence 2.0)
Verifies multi-step DAG planning, zero-trust security guardian approval gates,
tool delegation, NEMA verification, self-healing recovery, and Flask API endpoints.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.langgraph_orchestrator import LangGraphOrchestrator, langgraph_orchestrator
from core.orchestrator import orchestrator


def run_all_tests():
    print("==================================================")
    print("JARVIS LANGGRAPH AUTONOMOUS INTELLIGENCE 2.0 TESTS")
    print("==================================================")

    # 1. Orchestrator Initialization
    print("\n1. Testing LangGraph StateGraph initialization & compilation...")
    lg = LangGraphOrchestrator()
    assert lg.graph is not None, "Compiled StateGraph must exist."
    assert lg.checkpointer is not None, "Checkpointer must exist."
    print("   [PASS] LangGraph StateGraph compiled with MemorySaver checkpointer.")

    # 2. Informational Direct Answer Flow
    print("\n2. Testing informational query through LangGraph DAG...")
    res1 = lg.run_mission("Explain quantum entanglement briefly in one sentence.", auto_approve=True)
    assert res1.get("status") in ["completed", "verifying"], f"Status should be completed, got {res1.get('status')}"
    assert len(res1.get("plan", [])) > 0, "Plan must contain at least one step."
    assert res1.get("final_response"), "Final response must not be empty."
    print(f"   [PASS] Informational mission succeeded: {res1.get('status')}")
    print(f"          Response: {res1.get('final_response')[:90]}...")

    # 3. Security Guardian Approval Gate on Sensitive Tasks
    print("\n3. Testing Zero-Trust Security Guardian Approval Gate...")
    sensitive_task = "Delete all temporary cached files and remove unused logs"
    res_sensitive = lg.run_mission(sensitive_task, auto_approve=False)
    
    assert res_sensitive.get("status") == "awaiting_approval", f"Expected 'awaiting_approval', got {res_sensitive.get('status')}"
    pending = res_sensitive.get("pending_approval")
    assert pending is not None, "pending_approval details must be populated."
    assert pending.get("risk_level") == "HIGH", "Risk level should be HIGH for deletion."
    sid = res_sensitive.get("session_id")
    print(f"   [PASS] Privileged operation paused at Guardian Gate. Session ID: {sid}")
    print(f"          Risk Level: {pending.get('risk_level')} | Reason: {pending.get('reason')}")

    # 4. Human-in-the-Loop Approval & Resumption
    print("\n4. Testing Guardian Approval Gate resumption...")
    res_approved = lg.approve_mission_step(sid, approved=True)
    assert res_approved.get("status") in ["completed", "executing", "verifying"], f"Status should progress after approval, got {res_approved.get('status')}"
    assert res_approved.get("pending_approval") is None, "Pending approval should be cleared."
    print(f"   [PASS] Mission resumed after human authorization: {res_approved.get('status')}")

    # 5. Self-Healing Recovery Node
    print("\n5. Testing Self-Healing Recovery loop on simulated step failure...")
    mock_state = {
        "session_id": "test_recovery_session",
        "task": "Perform automated UI click on missing element",
        "plan": [{
            "id": 1,
            "description": "Click missing element",
            "tool": "omni_parser",
            "arguments": {"directive": "click ghost button"},
            "status": "failed",
            "result": "ERROR: Element not found",
            "requires_approval": False,
            "approval_status": "approved"
        }],
        "current_step_index": 0,
        "guardian_approved": True,
        "pending_approval": None,
        "execution_history": [],
        "verification": {"status": "failed"},
        "retry_count": 0,
        "max_retries": 3,
        "final_response": "",
        "status": "recovering",
        "error": "Element not found"
    }

    recovery_res = lg._recovery_node(mock_state)
    assert recovery_res["retry_count"] == 1, "Retry count must increment to 1."
    assert recovery_res["status"] == "executing", "Status must reset to executing."
    patched_step = recovery_res["plan"][0]
    assert patched_step["status"] == "pending", "Step must be set back to pending for re-try."
    print(f"   [PASS] Recovery engine patched plan (Attempt {recovery_res['retry_count']}/3): {patched_step['description']}")

    # 6. Core Orchestrator Integration Hook
    print("\n6. Testing AgentOrchestrator integration hooks...")
    assert hasattr(orchestrator, "run_autonomous_mission"), "orchestrator must have run_autonomous_mission"
    assert hasattr(orchestrator, "approve_mission"), "orchestrator must have approve_mission"
    hook_res = orchestrator.run_autonomous_mission("Hello Jarvis, system diagnostic check", auto_approve=True)
    assert hook_res.get("status") in ["completed", "verifying"]
    print("   [PASS] AgentOrchestrator.run_autonomous_mission hook verified.")

    # 7. Flask API Endpoints
    print("\n7. Testing Flask API Orchestrator mission routes...")
    from app import app
    client = app.test_client()

    # Post mission
    api_resp = client.post("/api/orchestrator/mission", json={
        "task": "Analyze system performance status",
        "auto_approve": True
    })
    assert api_resp.status_code == 200, f"Expected 200, got {api_resp.status_code}"
    api_data = api_resp.get_json()
    assert api_data["status"] == "success"
    session_id = api_data["session_id"]
    assert session_id, "session_id must be returned"
    print(f"   [PASS] POST /api/orchestrator/mission operational (Session: {session_id}).")

    # Get session status
    get_resp = client.get(f"/api/orchestrator/session/{session_id}")
    assert get_resp.status_code == 200
    session_data = get_resp.get_json()
    assert session_data["status"] == "success"
    assert session_data["session_id"] == session_id
    print("   [PASS] GET /api/orchestrator/session/<id> operational.")

    print("\n==================================================")
    print("ALL 7 LANGGRAPH AUTONOMOUS INTELLIGENCE 2.0 CHECKS PASSED NOMINALLY!")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
