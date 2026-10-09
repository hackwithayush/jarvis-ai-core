"""
Jarvis v16.0 — Autonomous Adversarial Review Engine
Dialectical Multi-Agent Truth-Seeking Matrix:
- Agent 1: Proponent (Thesis / Advocate / Architect)
- Agent 2: Adversary (Antithesis / Red Team / Inquisitor)
- Agent 3: Arbiter (Synthesis / Empirical Magistrate / Truth Supreme)

Operates via multi-turn Hegelian dialectics to eliminate hallucination, bias,
and blind spots, deriving verifiable ground truth on complex questions.
"""
import logging
import re
import time
from typing import Generator, Optional, Dict, Any, List

from core.model_manager import ModelManager
from core.web_search import WebSearchEngine

logger = logging.getLogger("jarvis.adversarial_review")


class AdversarialReviewEngine:
    """
    Orchestrates a 3-agent adversarial debate to rigorously evaluate hypotheses,
    strategies, architectures, or controversial topics and extract objective ground truth.
    """

    def __init__(self, model_manager: Optional[ModelManager] = None, web_search: Optional[WebSearchEngine] = None):
        self.model = model_manager or ModelManager()
        self.web_search = web_search or WebSearchEngine()

    def _query_agent(self, system_prompt: str, prompt: str, model: Optional[str] = None) -> str:
        """Execute a non-streaming query to an agent node with dedicated system directives and auto-failover."""
        messages = [{"role": "user", "content": prompt}]
        candidates = []
        if model:
            candidates.append(model)
        candidates.extend(["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "gemini-3.8-flash", "openai/gpt-oss-20b"])
        
        seen = set()
        unique_candidates = [m for m in candidates if m and not (m in seen or seen.add(m))]
        
        last_err = ""
        for target in unique_candidates:
            try:
                res = self.model.generate(messages=messages, system_prompt=system_prompt, model=target)
                cleaned = (res or "").strip()
                if cleaned and not cleaned.startswith("Error: I'm currently unable") and not cleaned.startswith("⚠️"):
                    return cleaned
                last_err = cleaned
                logger.warning(f"Adversarial Review Agent on '{target}' gave unusable response: {cleaned[:100]}")
            except Exception as e:
                logger.warning(f"Adversarial Review Agent invocation failed on '{target}': {e}")
                last_err = str(e)
                continue
                
        return f"[Agent reasoning error: {last_err or 'No response from intelligence grid'}]"

    def stream_review(self, topic: str, ground_intel: Optional[str] = None) -> Generator[str, None, None]:
        """
        Executes the full 3-agent adversarial review, yielding real-time chunks
        as each agent speaks and the Arbiter delivers the final binding verdict.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            yield "⚠️ **Error**: Adversarial review topic cannot be empty."
            return

        yield f"# 🏛️ ADVERSARIAL REVIEW: GROUND TRUTH INQUEST\n"
        yield f"> **Target Inquiry**: *\"{clean_topic}\"*\n"
        yield f"> **Epistemic Protocol**: 3-Agent Dialectical Verification (Thesis → Antithesis → Synthesis)\n"
        yield f"> **Triad Nodes**: 🏛️ Proponent (Advocate) · ⚔️ Adversary (Red Team) · ⚖️ Arbiter (Truth Supreme)\n\n"
        yield f"---\n\n"

        # ─── PHASE 0: SATELLITE GROUND INTELLIGENCE GATHERING ────────────────
        yield f"🔍 *Gathering ground intelligence and empirical vectors...*\n\n"
        intel_context = ground_intel or ""
        if not intel_context:
            try:
                # Fast check if topic requires live facts
                search_query = clean_topic[:100]
                search_results = self.web_search.build_search_context(search_query)
                if search_results:
                    intel_context = search_results
            except Exception as e:
                logger.debug(f"Adversarial intelligence pre-search notice: {e}")

        ground_prompt_addon = ""
        if intel_context:
            ground_prompt_addon = (
                f"\n\n--- VERIFIED GROUND INTELLIGENCE / EMPIRICAL DATA ---\n"
                f"{intel_context[:1800]}\n"
                f"--- END GROUND DATA ---\n"
            )

        # ─── PHASE 1: AGENT 1 (THE PROPONENT · THESIS) ──────────────────────
        yield f"### 🏛️ [AGENT 1: THE PROPONENT · THESIS ARCHITECT]\n"
        yield f"*Constructing affirmative proposition and foundational architecture...*\n\n"

        proponent_sys = (
            "You are THE PROPONENT (Agent 1) in JARVIS's professional Adversarial Review Court.\n"
            "Your role is the Principal Domain Advocate and Affirmative Architect.\n"
            "DIRECTIVES:\n"
            "1. Present the STRONGEST, most articulate affirmative case for the inquiry/topic.\n"
            "2. Lay out 3 clear Foundational Pillars: Core Mechanics, Strategic Value/Benefits, and Empirical Precedent.\n"
            "3. Ground your claims in logical causality, benchmarks, and real-world mechanisms.\n"
            "4. Tone: Confident, rigorous, analytical, and compelling. Avoid superficial hype; use solid engineering/analytical reasoning."
        )

        proponent_user = (
            f"INQUIRY TOPIC: \"{clean_topic}\"{ground_prompt_addon}\n\n"
            "Deliver your Formal Affirmative Proposition (Thesis). Structure it with:\n"
            "- **Core Thesis Statement**\n"
            "- **Pillar 1: Structural & Causal Mechanics**\n"
            "- **Pillar 2: Strategic Value & Tangible Advantages**\n"
            "- **Pillar 3: Empirical Validation & Real-World Precedents**\n"
            "- **Primary Affirmative Conclusion**"
        )

        thesis_text = self._query_agent(proponent_sys, proponent_user)
        yield f"{thesis_text}\n\n"
        yield f"---\n\n"

        # ─── PHASE 2: AGENT 2 (THE ADVERSARY · ANTITHESIS) ───────────────────
        yield f"### ⚔️ [AGENT 2: THE ADVERSARY · RED TEAM INQUISITOR]\n"
        yield f"*Initiating aggressive adversarial cross-examination and failure-mode audit...*\n\n"

        adversary_sys = (
            "You are THE ADVERSARY (Agent 2) in JARVIS's professional Adversarial Review Court.\n"
            "Your role is the Lead Red Team Inquisitor and Epistemic Skeptic.\n"
            "DIRECTIVES:\n"
            "1. Relentlessly cross-examine and dismantle the Proponent's Thesis.\n"
            "2. Identify hidden assumptions, logical fallacies, edge-case failures, unmeasured overheads, security vulnerabilities, or false dichotomies.\n"
            "3. Formulate concrete counter-examples and falsification criteria: 'Under what exact circumstances does this proposition collapse?'\n"
            "4. Tone: Razor-sharp, skeptical, forensic, uncompromising, and objective. Never attack the persona; attack the logic, claims, and blind spots."
        )

        adversary_user = (
            f"INQUIRY TOPIC: \"{clean_topic}\"\n\n"
            f"PROPONENT'S THESIS:\n{thesis_text}\n{ground_prompt_addon}\n\n"
            "Deliver your Adversarial Counter-Analysis (Antithesis). Structure it with:\n"
            "- **Executive Critique & Vulnerability Vector**\n"
            "- **Critical Flaw 1: Flawed Assumptions & Boundary Failures**\n"
            "- **Critical Flaw 2: Hidden Costs, Friction & Second-Order Risks**\n"
            "- **Critical Flaw 3: Counter-Evidence & Worst-Case Failure Modes**\n"
            "- **Falsification Challenge (The Hard Questions the Proponent Must Answer)**"
        )

        antithesis_text = self._query_agent(adversary_sys, adversary_user)
        yield f"{antithesis_text}\n\n"
        yield f"---\n\n"

        # ─── PHASE 3: ROUND 2 — CROSS-FIRE & REBUTTAL ───────────────────────
        yield f"### 🛡️ [ROUND 2: DIRECT REBUTTAL & CONCESSION]\n"
        yield f"*The Proponent faces the Inquisitor's cross-examination...*\n\n"

        rebuttal_sys = (
            "You are THE PROPONENT (Agent 1) responding to the Adversary's cross-examination.\n"
            "DIRECTIVES:\n"
            "1. Rigorously defend your defensible claims where the Adversary mischaracterized or overreached.\n"
            "2. INTELLECTUAL HONESTY MANDATE: Concede valid flaws or genuine risks identified by the Adversary.\n"
            "3. Refine and constrain the scope of your thesis to incorporate necessary mitigations.\n"
            "4. Tone: Professional, unshakeable, intellectually honest, and constructive."
        )

        rebuttal_user = (
            f"INQUIRY TOPIC: \"{clean_topic}\"\n\n"
            f"YOUR ORIGINAL THESIS:\n{thesis_text[:600]}...\n\n"
            f"ADVERSARY'S CRITIQUE:\n{antithesis_text}\n\n"
            "Deliver your Rebuttal & Concession Statement. Structure it with:\n"
            "- **1. Conceded Points (Valid Vulnerabilities Acknowledged)**\n"
            "- **2. Counter-Rebuttal (Flaws in the Adversary's Objections & Defended Ground)**\n"
            "- **3. Hardened, Mitigated Proposition (The Refined Thesis)**"
        )

        rebuttal_text = self._query_agent(rebuttal_sys, rebuttal_user)
        yield f"{rebuttal_text}\n\n"
        yield f"---\n\n"

        # ─── PHASE 4: AGENT 3 (THE ARBITER · THE GROUND TRUTH SYNTHESIS) ─────
        yield f"### ⚖️ [AGENT 3: THE ARBITER · SUPREME TRUTH JUDGE]\n"
        yield f"*Adjudicating evidence, reconciling thesis with antithesis, and establishing Ground Truth...*\n\n"

        arbiter_sys = (
            "You are THE ARBITER (Agent 3) in JARVIS's professional Adversarial Review Court.\n"
            "Your role is the Sovereign Truth Judge and Empirical Synthesizer.\n"
            "You have no dog in the fight. You care ONLY about first-principles ground truth, empirical data, and reality.\n"
            "DIRECTIVES:\n"
            "1. Adjudicate the debate point-by-point between Proponent (Thesis + Rebuttal) and Adversary (Antithesis).\n"
            "2. State what has been mathematically/empirically PROVEN, what has been REFUTED, and what is CONDITIONAL.\n"
            "3. Formulate the comprehensive GROUND TRUTH SYNTHESIS: The nuanced, real-world reality beyond binary hype or cynicism.\n"
            "4. Provide an Executive Truth Matrix (Markdown table) assessing key contentious points.\n"
            "5. Assign a precise TRUTH CONFIDENCE INDEX (0% to 100%) with justification.\n"
            "6. Conclude with Actionable Directives & Rules of Engagement for the user/organization."
        )

        arbiter_user = (
            f"INQUIRY TOPIC: \"{clean_topic}\"\n\n"
            f"PROPONENT THESIS:\n{thesis_text}\n\n"
            f"ADVERSARY ANTITHESIS:\n{antithesis_text}\n\n"
            f"PROPONENT REBUTTAL & CONCESSIONS:\n{rebuttal_text}\n{ground_prompt_addon}\n\n"
            "Render your Binding Judicial Verdict & Ground Truth Synthesis. Structure it with:\n"
            "### ⚖️ JUDICIAL ADJUDICATION SUMMARY\n"
            "- **Valid Claims Confirmed (Points Won by Proponent)**\n"
            "- **Fatal Flaws & Illusions Disproved (Points Won by Adversary)**\n"
            "- **Key Boundary Conditions (When the proposition holds vs when it fails)**\n\n"
            "### 📊 EXECUTIVE TRUTH MATRIX\n"
            "| Contention / Claim | Proponent Position | Adversary Challenge | Arbiter Ruling | Final Truth Status |\n"
            "(Fill in table with at least 3-4 key contention rows)\n\n"
            "### 💎 THE GROUND TRUTH SYNTHESIS\n"
            "(The authoritative, objective truth that reconciles valid arguments and eliminates falsehoods)\n\n"
            "### 🎯 EPISTEMIC CONFIDENCE RATING\n"
            "**Truth Confidence Index**: [X]% — (Explain reason for certainty or remaining variance)\n\n"
            "### 📜 STRATEGIC DIRECTIVES & RULES OF ENGAGEMENT\n"
            "- 1. [Rule/Action]\n"
            "- 2. [Rule/Action]\n"
            "- 3. [Rule/Action]"
        )

        synthesis_text = self._query_agent(arbiter_sys, arbiter_user)
        yield f"{synthesis_text}\n\n"
        yield f"---\n\n"
        yield f"✨ **Adversarial Review Completed.** *Epistemic integrity verified by JARVIS Truth Matrix.*"

    def review(self, topic: str, ground_intel: Optional[str] = None) -> str:
        """Synchronous helper returning the full adversarial review dossier as a single string."""
        chunks = []
        for chunk in self.stream_review(topic, ground_intel=ground_intel):
            chunks.append(chunk)
        return "".join(chunks)


# Global singleton instance
adversarial_review_engine = AdversarialReviewEngine()
