"""
Test Suite for JARVIS llama.cpp Local Inference Engine & Hardware Optimization
Tests hardware profiling (GPU/CPU/RAM), optimal hyperparameter calculation,
model discovery, local inference generation, performance benchmarking,
LangGraph workflow integration, and Flask API endpoints.
"""
import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.llama_engine import llama_engine, LlamaHardwareOptimizer
from core.model_manager import ModelManager
from core.langgraph_orchestrator import langgraph_orchestrator


class TestLlamaEngine(unittest.TestCase):
    def test_01_hardware_detection(self):
        """Verify host hardware detection discovers CPU, RAM, and NVIDIA GPU if present."""
        hw = LlamaHardwareOptimizer.detect_hardware()
        self.assertIn("cpu_cores", hw)
        self.assertGreater(hw["cpu_cores"], 0)
        self.assertIn("total_ram_gb", hw)
        self.assertGreater(hw["total_ram_gb"], 0)

        # Check optimal settings
        opts = hw.get("optimal_settings", {})
        self.assertIn("n_threads", opts)
        self.assertIn("n_gpu_layers", opts)
        self.assertIn("n_ctx", opts)
        self.assertIn("n_batch", opts)

        if hw["gpu"]["has_gpu"]:
            self.assertIsNotNone(hw["gpu"]["gpu_name"])
            self.assertGreater(hw["gpu"]["vram_total_mb"], 0)
            self.assertGreaterEqual(opts["n_gpu_layers"], 16)

    def test_02_model_discovery(self):
        """Verify model discovery scans local GGUF models and server models."""
        models_data = llama_engine.list_models()
        self.assertEqual(models_data.get("status"), "success")
        self.assertIn("server_models", models_data)
        self.assertIn("local_gguf_files", models_data)

        # Check that server models include installed models
        server_models = [m.get("name") for m in models_data.get("server_models", [])]
        self.assertTrue(any("llama" in name.lower() for name in server_models))

    def test_03_engine_status(self):
        """Verify engine status reporting."""
        status = llama_engine.get_status()
        self.assertIn("status", status)
        self.assertIn("hardware", status)
        self.assertIn("engine", status)
        self.assertTrue(status.get("server_reachable"))

    def test_04_local_inference_generation(self):
        """Verify local model inference generates response with token throughput metrics."""
        res = llama_engine.generate(
            prompt="Reply with the exact word: Affirmative.",
            model="llama3.2:latest",
            max_tokens=20,
            timeout=20
        )
        self.assertEqual(res.get("status"), "success")
        self.assertIn("response", res)
        self.assertGreater(res.get("tokens_generated", 0), 0)
        self.assertGreater(res.get("tokens_per_second", 0), 0)
        self.assertIn("hardware_used", res)

    def test_05_benchmark(self):
        """Verify local inference benchmark executes and rates performance."""
        bench = llama_engine.benchmark(
            model="llama3.2:latest",
            prompt="State one key law of physics in ten words.",
            max_tokens=32
        )
        self.assertEqual(bench.get("status"), "success")
        self.assertIn("performance_rating", bench)
        self.assertGreater(bench.get("tokens_per_second", 0), 0)
        self.assertIn("duration_seconds", bench)

    def test_06_model_manager_hardware_integration(self):
        """Verify ModelManager exposes hardware profile in its status report."""
        mgr = ModelManager()
        status = mgr.get_status()
        self.assertIn("hardware_profile", status)
        self.assertIn("gpu", status["hardware_profile"])

    def test_07_langgraph_llama_dag(self):
        """Verify LangGraph generates a DAG binding to llama_local tool for offline inference."""
        plan = langgraph_orchestrator._generate_dag("Run local llm benchmark on offline models")
        tools = [s.get("tool") for s in plan]
        self.assertIn("llama_local", tools)

    def test_08_flask_llama_endpoints(self):
        """Verify Flask REST endpoints for hardware status, model listing, and inference."""
        from app import app
        client = app.test_client()

        # Status endpoint
        res_status = client.get("/api/llama/status")
        self.assertEqual(res_status.status_code, 200)
        data_status = res_status.get_json()
        self.assertEqual(data_status.get("status"), "online")

        # Models endpoint
        res_models = client.get("/api/llama/models")
        self.assertEqual(res_models.status_code, 200)
        data_models = res_models.get_json()
        self.assertEqual(data_models.get("status"), "success")

        # Generate endpoint
        res_gen = client.post("/api/llama/generate", json={
            "prompt": "Say test passed in 3 words.",
            "model": "llama3.2:latest",
            "max_tokens": 15
        })
        self.assertEqual(res_gen.status_code, 200)
        data_gen = res_gen.get_json()
        self.assertEqual(data_gen.get("status"), "success")
        self.assertGreater(data_gen.get("tokens_per_second", 0), 0)


if __name__ == "__main__":
    unittest.main()
