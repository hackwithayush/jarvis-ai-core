"""
Test Suite for JARVIS OpenHands Autonomous Coding Agent
Tests syntax validation, path traversal security, backup/rollback,
test execution runner, self-healing loop logic, and API endpoints.
"""
import os
import sys
import unittest
import tempfile
import shutil

# Ensure jarvis root is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.openhands_agent import OpenHandsAgent, openhands_agent
from core.orchestrator import orchestrator, CodingAgentNode
from core.langgraph_orchestrator import langgraph_orchestrator


class TestOpenHandsCoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="jarvis_openhands_test_")
        cls.agent = OpenHandsAgent(workspace_root=cls.test_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_syntax_verification(self):
        """Verify AST-based syntax checking accepts valid code and catches syntax errors."""
        valid_code = "def add(a, b):\n    return a + b\n"
        is_valid, err = self.agent.verify_syntax(valid_code, "test.py")
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        invalid_code = "def broken(a, b:\n    return a +"
        is_valid, err = self.agent.verify_syntax(invalid_code, "test.py")
        self.assertFalse(is_valid)
        self.assertIn("SyntaxError", err)

    def test_02_path_traversal_protection(self):
        """Verify security guard prevents path traversal outside the workspace."""
        with self.assertRaises(PermissionError):
            self.agent._resolve_path("../../outside_file.py")

    def test_03_backup_and_rollback(self):
        """Verify file modifications create backups and rollback restores original content."""
        test_file = os.path.join(self.test_dir, "calc.py")
        original_content = "def calc(): return 42\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original_content)

        # Create backup
        backup_path = self.agent._create_backup(test_file)
        self.assertTrue(os.path.exists(backup_path))

        # Corrupt file
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def calc(): return 'broken'\n")

        # Rollback
        rollback_res = self.agent.rollback_file(backup_path, test_file)
        self.assertEqual(rollback_res.get("status"), "success")

        # Verify restored
        with open(test_file, "r", encoding="utf-8") as f:
            restored = f.read()
        self.assertEqual(restored, original_content)

    def test_04_read_source_file(self):
        """Verify safe source file reading and line counting."""
        sample_file = os.path.join(self.test_dir, "sample.py")
        sample_code = "# Line 1\n# Line 2\n# Line 3\n"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(sample_code)

        res = self.agent.read_source_file("sample.py")
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("total_lines"), 3)
        self.assertIn("Line 2", res.get("content"))

    def test_05_sandboxed_test_runner(self):
        """Verify runner executes python subprocess and captures pass/fail status."""
        # Simple inline test that passes
        res = self.agent.run_tests(test_command=[sys.executable, "-c", "import sys; sys.exit(0)"])
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("passed"))
        self.assertEqual(res.get("exit_code"), 0)

        # Inline test that fails
        res_fail = self.agent.run_tests(test_command=[sys.executable, "-c", "import sys; sys.exit(1)"])
        self.assertEqual(res_fail.get("status"), "failed")
        self.assertFalse(res_fail.get("passed"))
        self.assertEqual(res_fail.get("exit_code"), 1)

    def test_06_orchestrator_coding_node_bid(self):
        """Verify orchestrator selects CodingAgentNode for software development tasks."""
        node = CodingAgentNode()
        high_score = node.evaluate_confidence("Fix the bug in core/brain.py and run unit tests")
        self.assertGreaterEqual(high_score, 0.90)

        low_score = node.evaluate_confidence("What is the weather in New York?")
        self.assertLessEqual(low_score, 0.10)

        # Arbitrate task through AgentOrchestrator
        chosen = orchestrator.arbitrate("Refactor the python script to optimize database calls")
        self.assertEqual(chosen.name, "CodingAgent")

    def test_07_langgraph_coding_dag_generation(self):
        """Verify LangGraph orchestrator recognizes coding tasks and binds OpenHands node."""
        plan = langgraph_orchestrator._generate_dag("Implement function to calculate Fibonacci series")
        tools = [s.get("tool") for s in plan]
        self.assertIn("openhands", tools)

    def test_08_flask_coding_endpoints(self):
        """Verify Flask REST endpoints for code analysis and test execution."""
        from app import app
        client = app.test_client()

        # Analyze endpoint
        res = client.post("/api/coding/analyze", json={"goal": "Refactor logging mechanism"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("strategy", data)

        # Test runner endpoint with mock command
        res_test = client.post("/api/coding/test", json={"test_command": [sys.executable, "-c", "print('All good')"]})
        self.assertEqual(res_test.status_code, 200)
        data_test = res_test.get_json()
        self.assertTrue(data_test.get("passed"))


if __name__ == "__main__":
    unittest.main()
