"""
Test Suite for J.A.R.V.I.S. 4.0 — Mission Memory & Hardened Production Verification
Verifies:
1. Power loss and corrupted checkpoint recovery from secondary backup.
2. Storage-layer multi-user memory isolation and unauthorized deletion protection.
3. Coding-agent sandbox binary allowlist and environment secret purging.
4. Cloud failover secret scrubbing (zero credentials leaked to external models).
5. Mission Memory: Strategic objective decomposition into verifiable sequential milestones.
6. Cross-session continuity & detection of unfinished work after simulated reboot.
7. Flask REST API endpoints for Strategic Objectives and Mission Memory.
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
from core.mission_memory import MissionMemoryManager, mission_memory


class TestJarvis4MissionMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="jarvis4_test_")
        cls.coding_agent = OpenHandsAgent(workspace_root=cls.test_dir)
        cls.mission_mem = MissionMemoryManager(workspace_root=cls.test_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ─── 1. Checkpoint Integrity & Corrupted Backup Recovery ───────────────────

    def test_01_corrupted_checkpoint_recovers_from_backup(self):
        """Verify that a corrupted or truncated primary checkpoint auto-recovers from secondary .bak."""
        sid = f"power_loss_{os.urandom(4).hex()}"
        state_data = {
            "session_id": sid,
            "task": "Long-running research workflow",
            "plan": [{"id": 1, "description": "Step 1", "tool": "direct_answer", "status": "completed"}],
            "status": "executing",
            "current_step_index": 1
        }

        # Save checkpoint (creates primary and secondary backup)
        langgraph_orchestrator._save_session_checkpoint(sid, state_data)
        # Save a second time to ensure .bak is populated
        state_data["current_step_index"] = 2
        langgraph_orchestrator._save_session_checkpoint(sid, state_data)

        primary_path = os.path.join(langgraph_orchestrator.checkpoint_dir, f"{sid}.json")
        backup_path = f"{primary_path}.bak"

        self.assertTrue(os.path.exists(primary_path))
        self.assertTrue(os.path.exists(backup_path))

        # Simulate power failure / disk corruption: overwrite primary with invalid bytes
        with open(primary_path, "w", encoding="utf-8") as f:
            f.write("{ invalid_truncated_json: true, ... [POWER FAILURE] ...")

        # Load session — must detect corruption and gracefully recover from backup
        recovered_state = langgraph_orchestrator._load_session_checkpoint(sid)
        self.assertIsNotNone(recovered_state)
        self.assertEqual(recovered_state.get("session_id"), sid)
        # Primary file should be restored from valid backup
        with open(primary_path, "r", encoding="utf-8") as f:
            restored_data = json.load(f)
        self.assertEqual(restored_data.get("session_id"), sid)

    # ─── 2. Storage-Layer Memory Isolation & Deletion Protection ───────────────

    def test_02_memory_unauthorized_deletion_and_purge(self):
        """Verify user B cannot delete user A's memory, and user purge cleans only target user."""
        # Add memory for User Alice
        add_res = mem0_engine.add_memory("Alice's top-secret project is Project Starlight", user_id="user_alice")
        alice_mem_id = None
        if isinstance(add_res.get("results"), list) and len(add_res["results"]) > 0:
            alice_mem_id = add_res["results"][0].get("id")

        if alice_mem_id:
            # User Bob attempts to delete Alice's memory ID
            bob_del_res = mem0_engine.delete_memory(alice_mem_id, user_id="user_bob")
            self.assertEqual(bob_del_res.get("status"), "error")
            self.assertIn("Permission denied", bob_del_res.get("error", ""))

        # Purge all memories for a test user
        purge_res = mem0_engine.delete_all_user_memories(user_id="user_temp_purge")
        self.assertEqual(purge_res.get("status"), "success")
        self.assertEqual(purge_res.get("user_id"), "user_temp_purge")

    # ─── 3. Coding Sandbox & Environment Sanitization ──────────────────────────

    def test_03_coding_sandbox_binary_allowlist_and_secret_stripping(self):
        """Verify test runner rejects dangerous binaries and scrubs secrets from environment."""
        # 1. Binary allowlist check: reject bash, cmd, powershell, curl
        disallowed_res = self.coding_agent.run_tests(test_command=["cmd.exe", "/c", "dir"])
        self.assertEqual(disallowed_res.get("status"), "error")
        self.assertIn("Security restriction", disallowed_res.get("error", ""))

        # 2. Secret stripping verification: Python test script verifying environment
        env_test_code = (
            "import os, sys\n"
            "keys = ['GEMINI_API_KEY', 'OPENAI_API_KEY', 'SECRET_KEY']\n"
            "leaked = [k for k in keys if k in os.environ and os.environ[k]]\n"
            "if leaked:\n"
            "    print('LEAKED:', leaked)\n"
            "    sys.exit(1)\n"
            "sys.exit(0)\n"
        )
        res = self.coding_agent.run_tests(test_command=[sys.executable, "-c", env_test_code])
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("passed"))

    # ─── 4. Cloud Failover Secret Scrubbing ────────────────────────────────────

    def test_04_cloud_failover_secret_scrubbing(self):
        """Verify prompt secrets are thoroughly scrubbed before cloud transmission."""
        dirty_prompt = (
            "Deploy service with OpenAI key sk-1234567890abcdef1234567890abcdef1234567890abcdef and "
            "Gemini key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q and password: 'SuperSecretLocalPassword123!'."
        )
        scrubbed = llama_engine._scrub_sensitive_data(dirty_prompt)
        self.assertNotIn("sk-1234567890", scrubbed)
        self.assertNotIn("AIzaSyA1B2", scrubbed)
        self.assertNotIn("SuperSecretLocalPassword123!", scrubbed)
        self.assertIn("[REDACTED_LOCAL_SECRET]", scrubbed)

    # ─── 5. Strategic Objective Decomposition & Milestone Progression ──────────

    def test_05_mission_memory_objective_decomposition(self):
        """Verify strategic objective decomposes into sequential milestones with progress tracking."""
        obj = self.mission_mem.create_objective(
            goal="Build a personal autonomous AI research platform",
            user_id="Ayush"
        )
        self.assertEqual(obj.get("status"), "active")
        self.assertIn("milestones", obj)
        self.assertGreaterEqual(len(obj["milestones"]), 3)
        self.assertEqual(obj.get("progress_percent"), 0.0)
        self.assertEqual(obj.get("current_milestone_index"), 0)

        # Execute first milestone
        step_res = self.mission_mem.execute_next_milestone(obj["id"], auto_approve=True)
        self.assertEqual(step_res.get("status"), "success")
        self.assertEqual(step_res.get("milestone_completed"), 1)
        self.assertGreater(step_res.get("progress_percent"), 0.0)

        # Verify updated objective state
        updated = self.mission_mem.get_objective(obj["id"])
        self.assertEqual(updated.get("current_milestone_index"), 1)
        self.assertGreater(len(updated.get("decisions_log", [])), 0)

    # ─── 6. Windows Reboot Simulation & Unfinished Work Detection ──────────────

    def test_06_detect_unfinished_work_and_resume(self):
        """Verify Jarvis detects unfinished work across sessions and can resume from exact milestone."""
        # Create an objective
        obj = self.mission_mem.create_objective(
            goal="Develop workstation telemetry HUD dashboard",
            user_id="Ayush"
        )
        oid = obj["id"]

        # Simulate Windows reboot by creating a fresh MissionMemoryManager instance
        restarted_mem = MissionMemoryManager(workspace_root=self.test_dir)
        unfinished = restarted_mem.detect_unfinished_work()
        self.assertTrue(any(u.get("objective_id") == oid for u in unfinished))

        target_u = next(u for u in unfinished if u.get("objective_id") == oid)
        self.assertIn("prompt_to_resume", target_u)
        self.assertIn("workstation telemetry", target_u.get("title").lower())

        # Resume objective on restarted instance
        resume_res = restarted_mem.resume_objective(oid, authorized=True)
        self.assertEqual(resume_res.get("status"), "success")
        self.assertEqual(resume_res.get("milestone_completed"), 1)

    # ─── 7. Flask Strategic Objective Endpoints ────────────────────────────────

    def test_07_flask_objective_endpoints(self):
        """Verify REST APIs for strategic objective creation, listing, and inspection."""
        from app import app
        client = app.test_client()

        # Create objective
        res_create = client.post("/api/objective/create", json={
            "goal": "Build an intelligent code review bot",
            "user_id": "Ayush"
        })
        self.assertEqual(res_create.status_code, 200)
        data = res_create.get_json()
        oid = data.get("id")
        self.assertIsNotNone(oid)
        self.assertEqual(data.get("status"), "active")

        # List objectives
        res_list = client.get("/api/objective/list")
        self.assertEqual(res_list.status_code, 200)
        data_list = res_list.get_json()
        self.assertIn("objectives", data_list)

        # Get objective by ID
        res_get = client.get(f"/api/objective/{oid}")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.get_json()
        self.assertEqual(data_get.get("id"), oid)


if __name__ == "__main__":
    unittest.main()
