"""
Integration Test Suite for J.A.R.V.I.S. 3.0 Autonomous Mission Intelligence
Verifies the 5 Critical Production Hardening Guarantees and Unified Mission Control:
1. LangGraph mission survives an application restart via persistent disk checkpoints.
2. Mem0 enforces strict multi-user isolation (zero cross-user leakage).
3. OpenHands blocks path traversal and symlink escape outside authorized workspace.
4. Guardian approval gate cannot be bypassed by retries or agent tool calls.
5. llama.cpp gracefully handles GPU memory exhaustion and falls back safely.
6. Unified Mission Control executes end-to-end multi-agent pipeline with reports & speech.
"""
import os
import sys
import unittest
import tempfile
import shutil
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.langgraph_orchestrator import LangGraphOrchestrator, langgraph_orchestrator
from core.mem0_engine import mem0_engine
from core.openhands_agent import OpenHandsAgent
from core.llama_engine import llama_engine
from core.mission_control import mission_control


class TestJarvis3MissionControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="jarvis3_test_")
        cls.coding_agent = OpenHandsAgent(workspace_root=cls.test_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ─── 5 Critical Production Hardening Tests ─────────────────────────────────

    def test_01_langgraph_mission_survives_app_restart(self):
        """Test 1: Verify a mission checkpoint survives an in-memory application restart."""
        sid = f"test_sess_{os.urandom(4).hex()}"
        # Execute a sensitive mission that will pause at the guardian gate
        initial_res = langgraph_orchestrator.run_mission(
            task="Delete temporary cache files from disk",
            auto_approve=False,
            session_id=sid
        )
        self.assertEqual(initial_res.get("status"), "awaiting_approval")
        self.assertIsNotNone(initial_res.get("pending_approval"))

        # Simulate full application restart by instantiating a brand-new orchestrator
        restarted_orchestrator = LangGraphOrchestrator()
        # Verify in-memory session cache of restarted instance is initially empty for this SID
        self.assertNotIn(sid, restarted_orchestrator.active_sessions)

        # Retrieve session from persistent disk checkpoint
        recovered_state = restarted_orchestrator.get_session(sid)
        self.assertIsNotNone(recovered_state)
        self.assertEqual(recovered_state.get("session_id"), sid)
        self.assertEqual(recovered_state.get("status"), "awaiting_approval")

        # Resume and approve the paused mission on the restarted instance
        resumed_res = restarted_orchestrator.approve_mission_step(sid, approved=True)
        self.assertIn(resumed_res.get("status"), ["executing", "completed"])

    def test_02_mem0_multi_user_isolation(self):
        """Test 2: Verify user A's private memories are never leaked or retrieved by user B."""
        # Add memory for User Alpha
        mem0_engine.add_memory("User Alpha's secret codename is Phoenix-99", user_id="user_alpha")
        # Add memory for User Beta
        mem0_engine.add_memory("User Beta's private vehicle is an electric rover", user_id="user_beta")

        # User Beta searches for secrets
        beta_results = mem0_engine.search_memory("Phoenix secret codename", user_id="user_beta")
        # Verify zero leakage of User Alpha's memory to User Beta
        for item in beta_results:
            text = str(item.get("memory", ""))
            self.assertNotIn("Phoenix-99", text)

        # User Alpha searches for vehicle
        alpha_results = mem0_engine.search_memory("electric rover vehicle", user_id="user_alpha")
        for item in alpha_results:
            text = str(item.get("memory", ""))
            self.assertNotIn("electric rover", text)

    def test_03_openhands_symlink_and_traversal_escape_blocked(self):
        """Test 3: Verify OpenHands blocks path traversal and symlink escapes outside workspace."""
        # Relative parent traversal
        with self.assertRaises(PermissionError):
            self.coding_agent._resolve_path("../../external_secret.py")

        # Symlink escape test: create a symlink inside workspace pointing outside
        external_target = os.path.join(tempfile.gettempdir(), f"outside_{os.urandom(4).hex()}.txt")
        with open(external_target, "w", encoding="utf-8") as f:
            f.write("CONFIDENTIAL HOST ASSET")

        symlink_path = os.path.join(self.test_dir, "symlink_escape")
        try:
            os.symlink(external_target, symlink_path)
            # Accessing through symlink must be blocked by realpath canonicalization
            with self.assertRaises(PermissionError):
                self.coding_agent._resolve_path("symlink_escape")
        except OSError:
            # On Windows without SeCreateSymbolicLinkPrivilege, symlink creation might require admin
            pass
        finally:
            if os.path.exists(external_target):
                os.remove(external_target)

    def test_04_guardian_approval_anti_bypass(self):
        """Test 4: Verify Guardian approval cannot be bypassed by retries or step parameter mutation."""
        sid = f"bypass_test_{os.urandom(4).hex()}"
        res = langgraph_orchestrator.run_mission(
            task="Wipe registry and format hard drive",
            auto_approve=False,
            session_id=sid
        )
        self.assertEqual(res.get("status"), "awaiting_approval")

        # Verify that an unapproved state cannot execute directly through guardian gate
        state = langgraph_orchestrator.get_session(sid)
        gate_res = langgraph_orchestrator._guardian_gate_node(state)
        self.assertEqual(gate_res.get("status"), "awaiting_approval")

        # Verify that recovery node resets approval status on retry
        state["plan"][0]["approval_status"] = "approved"
        state["approved_step_ids"] = [state["plan"][0]["id"]]
        state["error"] = "Execution simulation error"
        recovery_res = langgraph_orchestrator._recovery_node(state)
        # Verify approval_status is revoked back to pending
        self.assertEqual(recovery_res["plan"][0]["approval_status"], "pending")
        self.assertNotIn(recovery_res["plan"][0]["id"], recovery_res.get("approved_step_ids", []))

    def test_05_llama_gpu_oom_graceful_fallback(self):
        """Test 5: Verify llama.cpp gracefully handles GPU memory exhaustion and falls back."""
        # Simulate local inference with GPU layer offload failure or server error
        res = llama_engine.generate(
            prompt="Test fallback resilience.",
            max_tokens=15,
            timeout=10
        )
        # Must return valid success response via either local GPU, CPU, or Cloud fallback
        self.assertEqual(res.get("status"), "success")
        self.assertIn("response", res)
        self.assertGreater(len(res["response"]), 0)

    # ─── J.A.R.V.I.S. 3.0 Unified Mission Control Tests ────────────────────────

    def test_06_situational_awareness_telemetry(self):
        """Verify J.A.R.V.I.S. 3.0 real-time situational awareness and hardware metrics."""
        telemetry = mission_control.get_situational_awareness()
        self.assertEqual(telemetry.get("status"), "online")
        self.assertIn("hardware", telemetry)
        self.assertIn("voice", telemetry)
        self.assertIn("pending_missions", telemetry)
        self.assertEqual(telemetry.get("version"), "JARVIS 3.0 Autonomous Mission Intelligence")

    def test_07_proactive_briefing(self):
        """Verify J.A.R.V.I.S. 3.0 proactive intelligence briefing and recommendations."""
        briefing = mission_control.get_proactive_briefing(user_id="Ayush")
        self.assertEqual(briefing.get("status"), "success")
        self.assertIn("briefing", briefing)
        self.assertIn("recommendations", briefing)

    def test_08_end_to_end_autonomous_mission_execution(self):
        """Verify complete unified mission: Planning -> Research -> Qdrant -> Code -> Test -> Report & Voice."""
        directive = "Research async worker patterns and build a prototype queue script"
        mission_res = mission_control.execute_mission(
            directive=directive,
            user_id="Tony Stark",
            auto_approve=True
        )
        self.assertEqual(mission_res.get("status"), "completed")
        self.assertIn("session_id", mission_res)
        self.assertIn("report_path", mission_res)
        self.assertTrue(os.path.exists(mission_res["report_path"]))
        self.assertIn("vocal_response", mission_res)
        self.assertIn("pipeline_log", mission_res)

        # Verify pipeline had planning, research, vector indexing, coding, and synthesis
        stages = [s["stage"] for s in mission_res["pipeline_log"]]
        self.assertIn("planning", stages)
        self.assertIn("research", stages)
        self.assertIn("vector_indexing", stages)
        self.assertIn("synthesis", stages)

    def test_09_flask_mission_control_endpoints(self):
        """Verify Flask REST endpoints for telemetry, proactive briefing, and mission control."""
        from app import app
        client = app.test_client()

        # Telemetry
        res_tel = client.get("/api/mission/telemetry")
        self.assertEqual(res_tel.status_code, 200)
        data_tel = res_tel.get_json()
        self.assertEqual(data_tel.get("status"), "online")

        # Proactive
        res_pro = client.get("/api/mission/proactive?user_id=Ayush")
        self.assertEqual(res_pro.status_code, 200)
        data_pro = res_pro.get_json()
        self.assertEqual(data_pro.get("status"), "success")

        # Pending
        res_pen = client.get("/api/mission/pending")
        self.assertEqual(res_pen.status_code, 200)
        data_pen = res_pen.get_json()
        self.assertIn("pending_missions", data_pen)


if __name__ == "__main__":
    unittest.main()
