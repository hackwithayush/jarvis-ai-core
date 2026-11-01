"""
JARVIS 4.0 — Mission Memory & Long-Term Objective Tracking
Decomposes complex multi-stage objectives into verifiable milestones,
persists architectural decisions across Windows reboots, detects unfinished work,
and orchestrates multi-session autonomous progression with human authorization gates.
"""
import os
import sys
import time
import json
import uuid
import shutil
import logging
from typing import Dict, Any, List, Optional, Tuple

import config
from core.model_manager import ModelManager

logger = logging.getLogger("jarvis.mission_memory")


class MissionMemoryManager:
    """
    Manages multi-day, long-term strategic objectives and persistent mission memory.
    Bridges high-level goals with discrete milestone executions.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.storage_dir = os.path.join(self.workspace_root, "data", "objectives")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.model_mgr = ModelManager()
        logger.info(f"JARVIS 4.0 Mission Memory active. Storage: {self.storage_dir}")

    # ─── Storage & Atomic Checkpointing ────────────────────────────────────────

    def _get_path(self, objective_id: str) -> str:
        return os.path.join(self.storage_dir, f"{objective_id}.json")

    def _save_objective(self, obj_data: Dict[str, Any]):
        """Saves objective state with atomic write and secondary backup protection."""
        oid = obj_data["id"]
        target_p = self._get_path(oid)
        backup_p = f"{target_p}.bak"
        temp_p = f"{target_p}.tmp"

        try:
            obj_data["updated_at"] = time.time()
            with open(temp_p, "w", encoding="utf-8") as f:
                json.dump(obj_data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())

            if os.path.exists(target_p):
                try:
                    shutil.copy2(target_p, backup_p)
                except Exception:
                    pass
                os.replace(temp_p, target_p)
            else:
                os.rename(temp_p, target_p)
        except Exception as e:
            logger.error(f"Failed to persist objective '{oid}': {e}")

    def get_objective(self, objective_id: str) -> Optional[Dict[str, Any]]:
        """Loads objective state from disk with backup recovery if primary is corrupted."""
        target_p = self._get_path(objective_id)
        backup_p = f"{target_p}.bak"

        # 1. Primary load
        if os.path.isfile(target_p):
            try:
                with open(target_p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Primary objective checkpoint corrupted for '{objective_id}': {e}. Trying backup...")

        # 2. Backup recovery
        if os.path.isfile(backup_p):
            try:
                with open(backup_p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                shutil.copy2(backup_p, target_p)
                return data
            except Exception:
                pass

        return None

    def list_objectives(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all recorded strategic objectives, optionally filtered by user."""
        results = []
        if not os.path.exists(self.storage_dir):
            return results

        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json") and not fname.endswith(".tmp.json"):
                oid = fname[:-5]
                data = self.get_objective(oid)
                if data:
                    if user_id is None or data.get("user_id") == user_id:
                        results.append(data)
        return results

    # ─── Objective Decomposition & Creation ────────────────────────────────────

    def create_objective(self, goal: str, user_id: str = "Ayush") -> Dict[str, Any]:
        """
        Deconstructs a strategic user goal into sequential, verifiable milestones.
        """
        oid = f"obj_{uuid.uuid4().hex[:8]}"
        logger.info(f"[MISSION MEMORY] Decomposing objective [{oid}]: '{goal}'")

        # Decompose using LLM into structured milestones
        milestones = self._decompose_goal_into_milestones(goal)

        obj_data = {
            "id": oid,
            "user_id": user_id,
            "title": goal[:60],
            "goal": goal,
            "status": "active",
            "current_milestone_index": 0,
            "total_milestones": len(milestones),
            "progress_percent": 0.0,
            "milestones": milestones,
            "decisions_log": [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "completed_at": None
        }

        self._save_objective(obj_data)
        logger.info(f"[MISSION MEMORY] Created objective '{obj_data['title']}' with {len(milestones)} milestones.")
        return obj_data

    def _decompose_goal_into_milestones(self, goal: str) -> List[Dict[str, Any]]:
        """Generates 3-5 structured sequential milestones for a strategic goal."""
        prompt = f"""
You are the J.A.R.V.I.S. Strategic Planning Subsystem.
Decompose this major objective into 3 to 5 discrete, sequential milestones:
"{goal}"

Return ONLY a valid JSON array of milestone objects with these keys:
- "id": integer starting from 1
- "title": concise milestone title
- "description": specific concrete deliverables and tasks
- "directive": exact execution prompt for Mission Control

Example JSON format:
[
  {{
    "id": 1,
    "title": "Architecture Specification & Research",
    "description": "Investigate required components and draft technical specification.",
    "directive": "Research architecture for {goal} and compile comparison report."
  }}
]
"""
        try:
            raw = self.model_mgr.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an autonomous strategic mission planner. Return ONLY valid JSON array."
            )
            clean = raw.replace("```json", "").replace("```", "").strip()
            milestones = json.loads(clean)
            if isinstance(milestones, list) and len(milestones) > 0:
                formatted = []
                for idx, m in enumerate(milestones):
                    formatted.append({
                        "id": idx + 1,
                        "title": m.get("title", f"Milestone {idx + 1}"),
                        "description": m.get("description", ""),
                        "directive": m.get("directive", f"Execute {m.get('title')}"),
                        "status": "pending",
                        "blocker": None,
                        "decisions": [],
                        "artifacts": [],
                        "started_at": None,
                        "completed_at": None
                    })
                return formatted
        except Exception as e:
            logger.warning(f"LLM milestone decomposition fallback: {e}")

        # Deterministic Fallback Decomposition
        return [
            {
                "id": 1,
                "title": "Technical Specification & Architecture",
                "description": f"Research design patterns and formulate implementation blueprint for: {goal}",
                "directive": f"Research and design architecture for {goal}",
                "status": "pending",
                "blocker": None,
                "decisions": [],
                "artifacts": [],
                "started_at": None,
                "completed_at": None
            },
            {
                "id": 2,
                "title": "Core Module & Prototype Construction",
                "description": f"Develop functional code prototype and automated tests for: {goal}",
                "directive": f"Build prototype code and test suite for {goal}",
                "status": "pending",
                "blocker": None,
                "decisions": [],
                "artifacts": [],
                "started_at": None,
                "completed_at": None
            },
            {
                "id": 3,
                "title": "Verification & Final Integration",
                "description": f"Verify all unit tests pass and compile executive mission report for: {goal}",
                "directive": f"Test prototype and verify integration for {goal}",
                "status": "pending",
                "blocker": None,
                "decisions": [],
                "artifacts": [],
                "started_at": None,
                "completed_at": None
            }
        ]

    # ─── Milestone Execution & Progression ─────────────────────────────────────

    def execute_next_milestone(
        self,
        objective_id: str,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Executes the current active milestone for an objective.
        Updates decision log, saves progress, and handles blockers.
        """
        obj = self.get_objective(objective_id)
        if not obj:
            return {"status": "error", "error": f"Objective '{objective_id}' not found."}

        idx = obj.get("current_milestone_index", 0)
        milestones = obj.get("milestones", [])

        if idx >= len(milestones):
            obj["status"] = "completed"
            obj["progress_percent"] = 100.0
            obj["completed_at"] = time.time()
            self._save_objective(obj)
            return {
                "status": "completed",
                "message": f"Objective '{obj['title']}' is fully completed (100%).",
                "objective": obj
            }

        ms = milestones[idx]
        ms["status"] = "in_progress"
        ms["started_at"] = time.time()
        self._save_objective(obj)

        logger.info(f"[MISSION MEMORY] Executing Milestone {ms['id']}/{len(milestones)}: '{ms['title']}'")

        # Delegate execution to MissionControlEngine
        from core.mission_control import mission_control
        mission_res = mission_control.execute_mission(
            directive=ms["directive"],
            user_id=obj.get("user_id", "Ayush"),
            auto_approve=auto_approve
        )

        # Check for pause / blocker
        if mission_res.get("status") == "awaiting_approval":
            ms["status"] = "blocked"
            ms["blocker"] = "Paused at Zero-Trust Guardian Gate: Privileged action requires human approval."
            obj["status"] = "blocked"
            self._save_objective(obj)
            return {
                "status": "blocked",
                "milestone": ms,
                "pending_approval": mission_res.get("pending_approval"),
                "message": f"Milestone {ms['id']} paused: Human supervisor authorization required."
            }

        # Check for completion
        if mission_res.get("status") == "completed":
            ms["status"] = "completed"
            ms["completed_at"] = time.time()
            if mission_res.get("report_path"):
                ms["artifacts"].append(mission_res["report_path"])
            if mission_res.get("prototype_path"):
                ms["artifacts"].append(mission_res["prototype_path"])

            decision_entry = f"Milestone {ms['id']} ({ms['title']}) completed successfully. Verified tests: {mission_res.get('tests_verified')}."
            ms["decisions"].append(decision_entry)
            obj.setdefault("decisions_log", []).append(decision_entry)

            # Advance to next milestone
            obj["current_milestone_index"] = idx + 1
            obj["progress_percent"] = round(((idx + 1) / len(milestones)) * 100, 1)

            if obj["current_milestone_index"] >= len(milestones):
                obj["status"] = "completed"
                obj["completed_at"] = time.time()

            self._save_objective(obj)

            return {
                "status": "success",
                "milestone_completed": ms["id"],
                "title": ms["title"],
                "progress_percent": obj["progress_percent"],
                "is_objective_completed": obj["status"] == "completed",
                "report_path": mission_res.get("report_path"),
                "vocal_briefing": mission_res.get("vocal_response"),
                "next_milestone": milestones[idx + 1]["title"] if idx + 1 < len(milestones) else None
            }

        # Handle failure
        ms["status"] = "blocked"
        ms["blocker"] = mission_res.get("error", "Execution failed.")
        obj["status"] = "blocked"
        self._save_objective(obj)
        return {
            "status": "failed",
            "milestone": ms,
            "error": ms["blocker"]
        }

    # ─── Windows Restart Continuity & Unfinished Work Detection ───────────────

    def detect_unfinished_work(self) -> List[Dict[str, Any]]:
        """
        Scans all objectives to detect unfinished milestones or paused work across reboots.
        """
        unfinished = []
        for obj in self.list_objectives():
            if obj.get("status") in ["active", "blocked", "in_progress"]:
                idx = obj.get("current_milestone_index", 0)
                milestones = obj.get("milestones", [])
                active_ms = milestones[idx] if idx < len(milestones) else None
                unfinished.append({
                    "objective_id": obj["id"],
                    "title": obj["title"],
                    "status": obj["status"],
                    "progress_percent": obj["progress_percent"],
                    "current_milestone": active_ms.get("title") if active_ms else "N/A",
                    "milestone_index": idx + 1,
                    "total_milestones": len(milestones),
                    "blocker": active_ms.get("blocker") if active_ms else None,
                    "prompt_to_resume": f"Sir, I detected unfinished work on '{obj['title']}' (Milestone {idx + 1}/{len(milestones)}). Ready to resume when authorized."
                })
        return unfinished

    def resume_objective(self, objective_id: str, authorized: bool = True) -> Dict[str, Any]:
        """
        Resumes an objective that was interrupted by a Windows reboot or paused at a gate.
        """
        obj = self.get_objective(objective_id)
        if not obj:
            return {"status": "error", "error": f"Objective '{objective_id}' not found."}

        if obj["status"] == "completed":
            return {"status": "completed", "message": "Objective is already completed."}

        # Clear blockers if authorized
        if authorized:
            obj["status"] = "active"
            idx = obj.get("current_milestone_index", 0)
            if idx < len(obj.get("milestones", [])):
                obj["milestones"][idx]["status"] = "pending"
                obj["milestones"][idx]["blocker"] = None
            self._save_objective(obj)

        return self.execute_next_milestone(objective_id, auto_approve=authorized)


# Global Singleton Instance
mission_memory = MissionMemoryManager()
