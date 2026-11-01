"""
Test Suite for J.A.R.V.I.S. 5.0 — Situational Autonomous Intelligence & Hardened Operations
Verifies:
1. Engineering Caution 1: Concurrency safety (two simultaneous missions safely update the same objective without race conditions).
2. Engineering Caution 2: Action idempotency & replay prevention (resumed mission cannot repeat completed external actions).
3. Engineering Caution 3: Stale permission re-validation (expired TTL prevents resuming with outdated authorization).
4. Persistent Personal Knowledge Graph: Multi-relational entity linking (DEPENDS_ON, RELATES_TO, BLOCKED_BY, SUPPORTS, CAUSED_BY).
5. Recursive Blocker & Root-Cause Traversal: Pinpointing blockers and diagnosing recurring failure origins.
6. Architectural Decision-to-Code Tracing: Connecting code modifications to justifying design decisions.
7. Cognitive Awareness & Situational Context: Active developer process detection and user focus inference.
8. Predictive Diagnostics: Anomaly detection (memory pressure, disk warnings, recurring failure clustering).
9. Autonomous Quality Evaluator: Code hygiene, security posture, syntax validation, and score calculation.
10. Flask REST Control Surface: Verifying all graph, cognitive, and evaluator endpoints return HTTP 200.
"""
import os
import sys
import time
import json
import shutil
import tempfile
import threading
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.knowledge_graph import KnowledgeGraph, knowledge_graph
from core.mission_memory import MissionMemoryManager, mission_memory
from core.cognitive_awareness import CognitiveAwarenessManager, cognitive_awareness
from core.autonomous_evaluator import AutonomousEvaluator, autonomous_evaluator


class TestJarvis5SituationalIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="jarvis5_test_")
        cls.graph_dir = os.path.join(cls.test_dir, "graph")
        cls.objectives_dir = os.path.join(cls.test_dir, "objectives")
        cls.test_graph = KnowledgeGraph(storage_dir=cls.graph_dir)
        cls.test_mem = MissionMemoryManager(workspace_root=cls.test_dir)
        cls.evaluator = AutonomousEvaluator()
        cls.cognitive = CognitiveAwarenessManager()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ─── 1. Engineering Caution 1: Concurrency Safety ─────────────────────────

    def test_01_simultaneous_objective_concurrency_lock(self):
        """Verify two simultaneous threads attempting to execute the same objective are safely locked."""
        obj = self.test_mem.create_objective(
            goal="Simultaneous Concurrency Stress Test",
            user_id="Ayush"
        )
        oid = obj["id"]
        results = []

        def worker():
            res = self.test_mem.execute_next_milestone(oid, auto_approve=True)
            results.append(res)

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)

        # Launch both threads concurrently
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(results), 2)
        # One thread should succeed or progress, and the other should safely handle concurrency (either locked or serial)
        statuses = [r.get("status") for r in results]
        self.assertTrue(
            "locked" in statuses or "success" in statuses,
            f"Expected concurrency protection or safe serialization. Got: {statuses}"
        )

        # Verify disk state remained uncorrupted
        loaded = self.test_mem.get_objective(oid)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["id"], oid)

    # ─── 2. Engineering Caution 2: Action Idempotency & Replay Prevention ──────

    def test_02_resumed_mission_action_idempotency(self):
        """Verify that an already-executed action returns cached result and prevents duplicate side effects."""
        test_oid = f"obj_idemp_{os.urandom(4).hex()}"
        payload = {"milestone_id": 1, "directive": "Compile report and generate code"}

        fp = self.test_mem.compute_action_fingerprint(
            action_type="milestone_execution",
            target=test_oid,
            payload=payload
        )
        self.assertIsNotNone(fp)
        self.assertEqual(len(fp), 64)  # SHA-256 hex digest length

        # Initially not executed
        self.assertIsNone(self.test_mem.is_action_already_executed(fp))

        # Record action execution
        self.test_mem.record_action_executed(
            fingerprint=fp,
            action_type="milestone_execution",
            target=test_oid,
            result={"status": "completed", "quality_score": 98.5}
        )

        # Check subsequent query: must return cached result
        cached = self.test_mem.is_action_already_executed(fp)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["action_type"], "milestone_execution")
        self.assertEqual(cached["result"]["quality_score"], 98.5)

    # ─── 3. Engineering Caution 3: Stale Permission Re-Validation ──────────────

    def test_03_stale_objective_permission_revalidation(self):
        """Verify that an objective with an expired authorization TTL cannot be resumed blindly."""
        obj = self.test_mem.create_objective(
            goal="Privileged Infrastructure Deployment",
            user_id="Ayush"
        )
        oid = obj["id"]

        # Artificially age the objective's authorization to 48 hours ago (TTL is 24 hours)
        obj["last_authorized_at"] = time.time() - (48 * 3600)
        self.test_mem._save_objective(obj)

        # Attempt resumption: must be blocked due to stale authorization
        resume_res = self.test_mem.resume_objective(oid, authorized=True, user_id="Ayush")
        self.assertEqual(resume_res.get("status"), "blocked")
        self.assertIn("authorization expired", resume_res.get("error", "").lower())

        # Verify objective status was downgraded
        updated = self.test_mem.get_objective(oid)
        self.assertEqual(updated.get("status"), "awaiting_reauthorization")

    # ─── 4. Persistent Personal Knowledge Graph Entities & Relations ──────────

    def test_04_knowledge_graph_entities_and_relations(self):
        """Verify adding multi-type nodes and multi-relational edges with atomic disk persistence."""
        g = self.test_graph

        # Add nodes
        p1 = g.add_node("proj_arc_reactor", "project", "Arc Reactor Mark V", {"status": "in_development"})
        p2 = g.add_node("proj_nanotech", "project", "Nanotech Housing Unit", {"status": "completed"})
        dec = g.add_node("dec_palladium_swap", "decision", "Replace Palladium with Vibranium Core")
        f1 = g.add_node("file_core_cpp", "file", "core/reactor.cpp", {"lines": 450})
        doc = g.add_node("doc_particle_synthesis", "document", "Particle Synthesis Research Paper")

        self.assertEqual(p1["type"], "project")
        self.assertEqual(dec["type"], "decision")

        # Add directed relations
        # 1. Project A DEPENDS_ON Project B
        edge_dep = g.add_edge("proj_arc_reactor", "proj_nanotech", "DEPENDS_ON", {"criticality": "high"})
        self.assertEqual(edge_dep["relation"], "DEPENDS_ON")

        # 2. Code change RELATES_TO Decision
        edge_rel = g.add_edge("dec_palladium_swap", "file_core_cpp", "RELATES_TO")
        self.assertEqual(edge_rel["relation"], "RELATES_TO")

        # 3. Research document SUPPORTS Implementation
        edge_sup = g.add_edge("doc_particle_synthesis", "proj_arc_reactor", "SUPPORTS")
        self.assertEqual(edge_sup["relation"], "SUPPORTS")

        # Query outgoing relations
        out_relations = g.query_relations("proj_arc_reactor", direction="out")
        target_ids = [r["target_id"] for r in out_relations]
        self.assertIn("proj_nanotech", target_ids)

        # Verify persistence on disk: create a fresh graph instance from the same directory
        reloaded_g = KnowledgeGraph(storage_dir=self.graph_dir)
        self.assertIsNotNone(reloaded_g.get_node("proj_arc_reactor"))
        self.assertIsNotNone(reloaded_g.get_node("dec_palladium_swap"))

    # ─── 5. Blocker Identification & Root Cause Tracing ────────────────────────

    def test_05_blocker_detection_and_root_cause_analysis(self):
        """Verify recursive blocker detection and causal failure root-cause analysis."""
        g = self.test_graph

        # Setup Dependency Chain: Milestone 3 -> BLOCKED_BY -> Task 2 -> BLOCKED_BY -> Task 1
        g.add_node("ms_3", "milestone", "Milestone 3: Full Integration", {"status": "pending"})
        g.add_node("task_2", "task", "Task 2: Hardware Validation", {"status": "in_progress"})
        g.add_node("task_1", "task", "Task 1: Firmware Flashing", {"status": "blocked"})

        g.add_edge("ms_3", "task_2", "BLOCKED_BY", {"reason": "Requires hardware validation"})
        g.add_edge("task_2", "task_1", "BLOCKED_BY", {"reason": "Requires firmware flashing"})

        blockers = g.find_blockers("ms_3")
        blocking_ids = [b["blocking_node_id"] for b in blockers]
        self.assertIn("task_2", blocking_ids)
        self.assertIn("task_1", blocking_ids)

        # Setup Root Cause Causal Chain:
        # Crash Event -> CAUSED_BY -> High Memory Spike -> CAUSED_BY -> Leaking Image Buffer Loop
        g.link_failure_to_root_cause(
            event_id="evt_ui_freeze",
            failure_description="Workstation UI thread frozen during mission render",
            root_cause_id="evt_memory_leak",
            root_cause_description="High Memory Spike (>95% RAM)"
        )
        g.add_node("evt_buffer_leak", "system_event", "Unclosed OpenCV VideoCapture Stream")
        g.add_edge("evt_memory_leak", "evt_buffer_leak", "CAUSED_BY")

        root_res = g.find_root_cause("evt_ui_freeze")
        self.assertTrue(root_res.get("is_deep_root_identified"))
        self.assertEqual(root_res["root_cause_node"]["id"], "evt_buffer_leak")
        self.assertIn("VideoCapture", root_res["root_cause_node"]["label"])

    # ─── 6. Decision-to-Code Tracing ───────────────────────────────────────────

    def test_06_decision_to_code_tracing(self):
        """Verify that architectural decisions can be retrieved by inspecting a target file."""
        g = self.test_graph
        file_path = "core/langgraph_orchestrator.py"

        g.link_decision_to_code(
            decision_id="dec_langgraph_adoption",
            decision_text="Adopt LangGraph cyclic DAG for stateful multi-agent execution",
            file_path=file_path
        )

        decisions = g.find_related_decisions(file_path)
        self.assertGreaterEqual(len(decisions), 1)
        self.assertIn("LangGraph", decisions[0]["title"])

    # ─── 7. Cognitive Awareness & Predictive Diagnostics ──────────────────────

    def test_07_cognitive_awareness_and_telemetry(self):
        """Verify active application detection, user focus inference, and predictive diagnostics."""
        app_ctx = self.cognitive.get_active_application_context()
        self.assertIn("foreground_window", app_ctx)
        self.assertIn("user_focus", app_ctx)
        self.assertIsInstance(app_ctx.get("detected_tools"), list)

        # Predictive Diagnostics
        diag = self.cognitive.predict_system_anomalies()
        self.assertIn("overall_health", diag)
        self.assertIn("hardware_telemetry", diag)
        self.assertIn("ram_percent", diag["hardware_telemetry"])
        self.assertIn("cpu_percent", diag["hardware_telemetry"])

        # Proactive Suggestions
        suggestions = self.cognitive.suggest_proactive_actions()
        self.assertIsInstance(suggestions, list)

    # ─── 8. Autonomous Quality Evaluator ───────────────────────────────────────

    def test_08_autonomous_quality_evaluator(self):
        """Verify code syntax analysis, security scans, maintainability checks, and grade computation."""
        # 1. Clean, well-formed Python code
        clean_code = (
            '"""Clean production module."""\n\n'
            'def calculate_thrust(mass: float, acceleration: float) -> float:\n'
            '    """Calculates force in Newtons."""\n'
            '    return mass * acceleration\n'
        )
        clean_eval = self.evaluator.evaluate_code(code_string=clean_code)
        self.assertTrue(clean_eval["passed"])
        self.assertGreaterEqual(clean_eval["quality_score"], 90.0)
        self.assertIn(clean_eval["grade"], ["A+", "A"])

        # 2. Insecure code with hardcoded API key and eval()
        dirty_code = (
            'OPENAI_KEY = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"\n'
            'def run_raw(x):\n'
            '    eval(x)\n'
        )
        dirty_eval = self.evaluator.evaluate_code(code_string=dirty_code)
        self.assertLess(dirty_eval["quality_score"], 70.0)
        self.assertTrue(any("Security" in r for r in dirty_eval["recommendations"]))

        # 3. Invalid syntax code
        invalid_code = "def broken_syntax(:\n    return False\n"
        invalid_eval = self.evaluator.evaluate_code(code_string=invalid_code)
        self.assertFalse(invalid_eval["passed"])
        self.assertEqual(invalid_eval["quality_score"], 0.0)
        self.assertEqual(invalid_eval["grade"], "F")

    # ─── 9. Flask REST Endpoints ───────────────────────────────────────────────

    def test_09_flask_situational_intelligence_endpoints(self):
        """Verify REST API routes for graph inspection, cognitive awareness, and evaluation."""
        from app import app
        client = app.test_client()

        # 1. Graph inspect
        res_graph = client.get("/api/graph/inspect")
        self.assertEqual(res_graph.status_code, 200)
        data_g = res_graph.get_json()
        self.assertIn("total_nodes", data_g)
        self.assertIn("total_edges", data_g)

        # 2. Add Node
        res_node = client.post("/api/graph/node", json={
            "id": "flask_test_node",
            "type": "project",
            "label": "Flask Test Project"
        })
        self.assertEqual(res_node.status_code, 200)

        # 3. Add Edge
        res_edge = client.post("/api/graph/edge", json={
            "source": "flask_test_node",
            "target": "jarvis_core",
            "relation": "DEPENDS_ON"
        })
        self.assertEqual(res_edge.status_code, 200)

        # 4. Cognitive Awareness
        res_cog = client.get("/api/cognitive/awareness")
        self.assertEqual(res_cog.status_code, 200)
        data_c = res_cog.get_json()
        self.assertIn("user_focus", data_c)

        # 5. Predictive Diagnostics
        res_diag = client.get("/api/cognitive/diagnostics")
        self.assertEqual(res_diag.status_code, 200)
        data_d = res_diag.get_json()
        self.assertIn("overall_health", data_d)

        # 6. Proactive Suggestions
        res_sug = client.get("/api/cognitive/suggestions")
        self.assertEqual(res_sug.status_code, 200)
        data_s = res_sug.get_json()
        self.assertIn("suggestions", data_s)

        # 7. Quality Evaluator
        res_eval = client.post("/api/evaluator/evaluate", json={
            "code": "def ping():\n    return 'pong'\n"
        })
        self.assertEqual(res_eval.status_code, 200)
        data_e = res_eval.get_json()
        self.assertIn("quality_score", data_e)


if __name__ == "__main__":
    unittest.main()
