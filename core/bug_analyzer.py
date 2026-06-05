"""
Legend Bug Analyzer — Autonomous System Diagnostics
Scans the codebase for logic errors, anti-patterns, and architectural weaknesses.
"""
import ast
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class LegendBugAnalyzer:
    """Autonomous Engine for codebase health and bug detection."""
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.findings = []

    def scan_project(self) -> List[Dict]:
        """Deep scan the entire project directory."""
        self.findings = []
        logger.info("Legend Analyzer: Initiating Autonomous Deep Scan...")
        
        for root, dirs, files in os.walk(self.root_dir):
            # Exclude virtual env folders and node_modules to prevent scanning third-party libraries
            skip_dirs = {"venv", ".venv", ".git", "__pycache__", "node_modules", "Lib", "Scripts", "Include"}
            if any(d in root.split(os.sep) for d in skip_dirs):
                continue
                
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    self._analyze_file(filepath)
                    
        return self.findings

    def _analyze_file(self, filepath: str):
        """Perform heuristic analysis on a specific file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            
            tree = ast.parse(code)
            rel_path = os.path.relpath(filepath, self.root_dir)
            
            # Heuristic 1: Bare Except Clauses
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    self._report(rel_path, node.lineno, "CRITICAL", 
                                "Bare 'except:' found. This hides all errors and causes silent failures.")

                # Heuristic 2: Large Functions (Complexity Warning)
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) > 50:
                        self._report(rel_path, node.lineno, "WARNING", 
                                    f"Function '{node.name}' is too large ({len(node.body)} lines). Refactor required.")

                # Heuristic 3: Hardcoded Secrets (Simple check)
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and any(x in target.id.lower() for x in ["key", "secret", "token", "password"]):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                if len(node.value.value) > 10:
                                    self._report(rel_path, node.lineno, "SECURITY", 
                                                f"Potential hardcoded secret in variable '{target.id}'.")

                # Heuristic 4: Infinite Loop Potential
                if isinstance(node, ast.While):
                    if isinstance(node.test, ast.Constant) and node.test.value is True:
                        # Check if there's a break or return
                        has_exit = False
                        for subnode in ast.walk(node):
                            if isinstance(subnode, (ast.Break, ast.Return)):
                                has_exit = True
                                break
                        if not has_exit:
                            self._report(rel_path, node.lineno, "ERROR", 
                                        "Infinite loop detected with no exit condition (break/return).")

        except Exception as e:
            logger.error(f"Analyzer failed on {filepath}: {e}")

    def _report(self, file: str, line: int, severity: str, message: str):
        self.findings.append({
            "file": file,
            "line": line,
            "severity": severity,
            "message": message
        })

def run_autonomous_scan(root_path: str):
    analyzer = LegendBugAnalyzer(root_path)
    return analyzer.scan_project()
