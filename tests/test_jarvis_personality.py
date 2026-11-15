"""
J.A.R.V.I.S. Personality, Character & Operating Charter Test Suite
==================================================================
Tests:
1. Constitutional Operating Charter (Articles I - VII)
2. The Intelligent Gentleman signature archetype & secondary archetypes
3. Autonomy Levels (Conservative, Balanced, Advanced)
4. Humour Level calibration & dynamic directives
5. Voice Accent mappings (British, American, Indian)
6. Canonical Spoken Scenario Phrases
7. Atomic serialization & disk persistence
8. REST API endpoints (/api/personality, /api/personality/charter, /api/personality/samples, /api/tts)
"""

import os
import json
import unittest
import tempfile
from core.personality import (
    JarvisPersonalityEngine,
    OPERATING_CHARTER,
    PERSONALITY_ARCHETYPES,
    VOICE_ACCENTS,
    AUTONOMY_LEVELS,
    personality_engine
)


class TestJarvisPersonalityEngine(unittest.TestCase):
    """Unit tests for the core JarvisPersonalityEngine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = JarvisPersonalityEngine(data_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_operating_charter_integrity(self):
        """Verify the 7 constitutional articles of J.A.R.V.I.S. are complete."""
        charter = self.engine.get_charter()
        self.assertEqual(len(charter["articles"]), 7)
        article_names = [a["name"] for a in charter["articles"]]
        self.assertIn("Identity", article_names)
        self.assertIn("Primary Mission", article_names)
        self.assertIn("Intelligence", article_names)
        self.assertIn("Autonomy", article_names)
        self.assertIn("Privacy and Security", article_names)
        self.assertIn("Communication", article_names)
        self.assertIn("Loyalty and Judgment", article_names)

    def test_02_intelligent_gentleman_archetype(self):
        """Verify The Intelligent Gentleman signature personality configuration."""
        gentleman = PERSONALITY_ARCHETYPES["intelligent_gentleman"]
        self.assertEqual(gentleman["name"], "The Intelligent Gentleman")
        self.assertIn("Calm", gentleman["tagline"])
        self.assertIn("Intelligent", gentleman["tagline"])
        self.assertIn("Loyal", gentleman["tagline"])
        self.assertEqual(gentleman["default_voice"], "en-GB-RyanNeural")
        self.assertEqual(gentleman["default_accent"], "british")
        
        # Verify traits
        traits = gentleman["traits"]
        for trait in ["Intelligent", "Loyal", "Calm", "Witty", "Honest", "Proactive", "Discreet", "Adaptive"]:
            self.assertIn(trait, traits)

    def test_03_voice_accents_supported(self):
        """Verify British, American, and Indian English accents are available."""
        self.assertIn("british", VOICE_ACCENTS)
        self.assertIn("american", VOICE_ACCENTS)
        self.assertIn("indian", VOICE_ACCENTS)
        self.assertEqual(VOICE_ACCENTS["british"]["primary_voice"], "en-GB-RyanNeural")
        self.assertEqual(VOICE_ACCENTS["american"]["primary_voice"], "en-US-ChristopherNeural")
        self.assertEqual(VOICE_ACCENTS["indian"]["primary_voice"], "en-IN-PrabhatNeural")

    def test_04_autonomy_levels(self):
        """Verify Conservative, Balanced, and Advanced autonomy levels."""
        self.assertIn("conservative", AUTONOMY_LEVELS)
        self.assertIn("balanced", AUTONOMY_LEVELS)
        self.assertIn("advanced", AUTONOMY_LEVELS)

    def test_05_humour_level_bounds_and_directives(self):
        """Verify humour slider updates bounds and reflects in system directives."""
        # Test 0%
        self.engine.update_settings({"humour_level": 0})
        self.assertEqual(self.engine.config["humour_level"], 0)
        directive_0 = self.engine.generate_system_directive()
        self.assertIn("HUMOUR: 0% (Pure business)", directive_0)

        # Test 55% (Gentleman Standard)
        self.engine.update_settings({"humour_level": 55})
        self.assertEqual(self.engine.config["humour_level"], 55)
        directive_55 = self.engine.generate_system_directive()
        self.assertIn("HUMOUR: 55%", directive_55)
        self.assertIn("The Intelligent Gentleman standard", directive_55)

        # Test bounds clipping (-10 -> 0, 150 -> 100)
        self.engine.update_settings({"humour_level": -10})
        self.assertEqual(self.engine.config["humour_level"], 0)
        self.engine.update_settings({"humour_level": 150})
        self.assertEqual(self.engine.config["humour_level"], 100)

    def test_06_user_title_and_canonical_samples(self):
        """Verify custom user titles reflect in spoken scenario phrases."""
        # Default: Sir
        self.engine.update_settings({"user_title": "Sir"})
        samples_sir = self.engine.get_sample_phrases()
        self.assertIn("Good morning, Sir.", samples_sir["starting_day"])
        self.assertIn("Task completed, Sir.", samples_sir["task_completed"])
        self.assertIn("Certainly, Sir.", samples_sir["humour_wit"])

        # Customized: Boss
        self.engine.update_settings({"user_title": "Boss"})
        samples_boss = self.engine.get_sample_phrases()
        self.assertIn("Good morning, Boss.", samples_boss["starting_day"])
        self.assertIn("Task completed, Boss.", samples_boss["task_completed"])

    def test_07_persistence_across_instances(self):
        """Verify personality settings persist atomically to disk and reload."""
        self.engine.update_settings({
            "assistant_name": "J.A.R.V.I.S. Mark V",
            "user_title": "Mr. Stark",
            "personality": "tactical",
            "humour_level": 70,
            "autonomy_level": "advanced",
            "voice_accent": "british"
        })

        # New instance pointing to same storage
        engine2 = JarvisPersonalityEngine(data_dir=self.temp_dir)
        settings = engine2.get_settings()
        self.assertEqual(settings["assistant_name"], "J.A.R.V.I.S. Mark V")
        self.assertEqual(settings["user_title"], "Mr. Stark")
        self.assertEqual(settings["personality"], "tactical")
        self.assertEqual(settings["humour_level"], 70)
        self.assertEqual(settings["autonomy_level"], "advanced")


class TestJarvisPersonalityAPI(unittest.TestCase):
    """Integration tests for personality API endpoints in app.py."""

    @classmethod
    def setUpClass(cls):
        from app import app
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_08_get_personality_api(self):
        """Verify GET /api/personality returns current settings and metadata."""
        res = self.client.get("/api/personality")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertIn("current", data)
        self.assertIn("archetypes", data)
        self.assertIn("voice_accents", data)
        self.assertIn("autonomy_levels", data)
        self.assertIn("charter", data)
        self.assertIn("sample_phrases", data)

    def test_09_post_personality_api(self):
        """Verify POST /api/personality saves updates successfully."""
        payload = {
            "assistant_name": "J.A.R.V.I.S.",
            "user_title": "Sir",
            "personality": "intelligent_gentleman",
            "humour_level": 55,
            "autonomy_level": "balanced",
            "voice_accent": "british"
        }
        res = self.client.post("/api/personality", json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["settings"]["personality"], "intelligent_gentleman")
        self.assertEqual(data["settings"]["humour_level"], 55)

    def test_10_get_charter_api(self):
        """Verify GET /api/personality/charter returns the 7 articles."""
        res = self.client.get("/api/personality/charter")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["charter"]["articles"]), 7)

    def test_11_tts_endpoint_resilience(self):
        """Verify POST /api/tts handles speech synthesis without raising 400/500."""
        res = self.client.post(
            "/api/tts",
            data=json.dumps({"text": "Systems online and fully synchronized with Stark Core, sir."}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "audio/mpeg")
        self.assertGreater(len(res.data), 500)


if __name__ == "__main__":
    unittest.main()
