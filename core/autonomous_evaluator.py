"""
JARVIS 5.0 — Autonomous Quality Evaluator
Measures the engineering quality, safety, and correctness of completed work,
evaluating code hygiene, security posture, syntax integrity, and test performance.
Produces an objective quality score (0-100), categorical grade, and recommendations.
"""
import os
import ast
import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("jarvis.evaluator")


class AutonomousEvaluator:
    """
    Evaluates completed mission prototypes, code files, and test results.
    Computes an objective composite quality score and categorical grade.
    """

    def __init__(self):
        logger.info("JARVIS 5.0 Autonomous Quality Evaluator active.")

    def evaluate_code(
        self,
        code_string: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a code string or file for syntax, hygiene, security, and structure.
        """
        source = code_string
        filename = file_path or "inline_code.py"

        if file_path and os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
            except Exception as e:
                return {
                    "passed": False,
                    "score": 0.0,
                    "grade": "F",
                    "error": f"Failed to read file '{file_path}': {e}"
                }

        if not source:
            return {
                "passed": False,
                "score": 0.0,
                "grade": "F",
                "error": "No code content provided for evaluation."
            }

        # 1. Syntax Integrity Analysis (Weight: 30%)
        syntax_score, syntax_issues = self._analyze_syntax(source, filename)

        # 2. Security Posture Analysis (Weight: 40%)
        security_score, security_issues = self._analyze_security(source)

        # 3. Maintainability & Hygiene Analysis (Weight: 30%)
        hygiene_score, hygiene_issues = self._analyze_hygiene(source, filename)

        # Composite Score Calculation: Syntax errors invalidate runnable code entirely
        if syntax_score == 0.0:
            total_score = 0.0
            grade = "F"
            passed = False
        else:
            total_score = round(
                (syntax_score * 0.30) +
                (security_score * 0.40) +
                (hygiene_score * 0.30),
                1
            )
            grade = self._calculate_grade(total_score)
            passed = total_score >= 70.0 and security_score >= 70.0

        all_recommendations = []
        for issue in security_issues:
            all_recommendations.append(f"[Security] {issue}")
        for issue in syntax_issues:
            all_recommendations.append(f"[Syntax] {issue}")
        for issue in hygiene_issues:
            all_recommendations.append(f"[Maintainability] {issue}")

        if not all_recommendations:
            all_recommendations.append("Code adheres to highest engineering standards.")

        return {
            "passed": passed,
            "quality_score": total_score,
            "grade": grade,
            "breakdown": {
                "syntax_integrity": syntax_score,
                "security_posture": security_score,
                "code_hygiene": hygiene_score
            },
            "metrics": {
                "total_lines": len(source.splitlines()),
                "total_characters": len(source),
                "issues_detected": len(syntax_issues) + len(security_issues) + len(hygiene_issues)
            },
            "recommendations": all_recommendations,
            "evaluated_at": time.time()
        }

    def evaluate_milestone_deliverables(
        self,
        prototype_path: Optional[str] = None,
        test_results: Optional[Dict[str, Any]] = None,
        report_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates overall milestone completeness combining code, tests, and documentation.
        """
        code_score = 80.0
        code_eval = None
        if prototype_path and os.path.isfile(prototype_path):
            code_eval = self.evaluate_code(file_path=prototype_path)
            code_score = code_eval["quality_score"]

        # Test Results Scoring
        test_score = 0.0
        if test_results:
            if test_results.get("passed", False):
                test_score = 100.0
            else:
                test_score = 25.0
        else:
            test_score = 70.0  # Assumed neutral if no executable tests

        # Documentation / Report Scoring
        doc_score = 0.0
        if report_path and os.path.isfile(report_path):
            doc_score = 100.0
        else:
            doc_score = 50.0

        # Weighted Milestone Score: 40% Code, 40% Tests, 20% Docs
        composite = round((code_score * 0.40) + (test_score * 0.40) + (doc_score * 0.20), 1)
        grade = self._calculate_grade(composite)

        return {
            "milestone_quality_score": composite,
            "grade": grade,
            "passed": composite >= 70.0,
            "code_evaluation": code_eval,
            "test_verified": test_results.get("passed", False) if test_results else True,
            "report_present": bool(report_path and os.path.isfile(report_path)),
            "evaluated_at": time.time()
        }

    # ─── Internal Analyzers ───────────────────────────────────────────────────

    def _analyze_syntax(self, source: str, filename: str) -> Tuple[float, List[str]]:
        """Verifies Python AST parseability without execution."""
        issues = []
        if filename.endswith(".py") or "def " in source or "import " in source:
            try:
                ast.parse(source)
                return 100.0, []
            except SyntaxError as e:
                issues.append(f"SyntaxError at line {e.lineno}: {e.msg}")
                return 0.0, issues
            except Exception as e:
                issues.append(f"Parsing error: {e}")
                return 0.0, issues
        return 100.0, []

    def _analyze_security(self, source: str) -> Tuple[float, List[str]]:
        """Scans for potential security liabilities, secret leakage, and risky calls."""
        score = 100.0
        issues = []

        # 1. Hardcoded Secrets
        secret_patterns = [
            (r'AIzaSy[A-Za-z0-9_-]{33}', "Potential hardcoded Google API key detected."),
            (r'sk-[A-Za-z0-9]{48,}', "Potential hardcoded OpenAI API key detected."),
            (r'gsk_[A-Za-z0-9]{48,}', "Potential hardcoded Groq API key detected."),
            (r'(?i)password\s*=\s*["\'][^"\']{6,}["\']', "Hardcoded password assignment detected.")
        ]
        for pat, desc in secret_patterns:
            if re.search(pat, source):
                score -= 45.0
                issues.append(desc)

        # 2. Dangerous Execution Patterns
        dangerous_patterns = [
            (r'\beval\s*\(', "Use of eval() detected (arbitrary code execution risk)."),
            (r'\bexec\s*\(', "Use of exec() detected (code injection hazard)."),
            (r'shell\s*=\s*True', "Subprocess with shell=True detected (command injection hazard)."),
            (r'os\.system\s*\(', "Direct os.system() invocation detected.")
        ]
        for pat, desc in dangerous_patterns:
            if re.search(pat, source):
                score -= 35.0
                issues.append(desc)

        return max(0.0, score), issues

    def _analyze_hygiene(self, source: str, filename: str) -> Tuple[float, List[str]]:
        """Evaluates maintainability, structure, and docstring coverage."""
        score = 100.0
        issues = []

        # 1. Bare Except Clauses
        if re.search(r'except\s*:', source):
            score -= 15.0
            issues.append("Bare 'except:' clause detected; catch specific exceptions.")

        # 2. Lingering TODO or FIXME markers
        todos = re.findall(r'(?i)(TODO|FIXME|XXX):?', source)
        if len(todos) > 0:
            score -= min(15.0, len(todos) * 5.0)
            issues.append(f"Found {len(todos)} incomplete TODO/FIXME markers in code.")

        # 3. Python Function Docstrings Check
        if filename.endswith(".py"):
            try:
                tree = ast.parse(source)
                funcs = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
                if funcs:
                    missing_doc = sum(1 for f in funcs if not ast.get_docstring(f))
                    if missing_doc > 0:
                        score -= min(20.0, (missing_doc / len(funcs)) * 25.0)
                        issues.append(f"{missing_doc}/{len(funcs)} functions lack docstrings.")
            except Exception:
                pass

        return max(0.0, score), issues

    def _calculate_grade(self, score: float) -> str:
        if score >= 95.0:
            return "A+"
        if score >= 88.0:
            return "A"
        if score >= 80.0:
            return "B+"
        if score >= 70.0:
            return "B"
        if score >= 60.0:
            return "C"
        return "F"


# Global Singleton Instance
autonomous_evaluator = AutonomousEvaluator()
