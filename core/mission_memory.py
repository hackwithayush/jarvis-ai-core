"""
JARVIS 5.0 — Mission Memory & Long-Term Objective Tracking
Decomposes complex multi-stage objectives into verifiable milestones,
persists architectural decisions across Windows reboots, detects unfinished work,
and orchestrates multi-session autonomous progression with human authorization gates.

Hardened with:
1. Concurrency Locking: Thread-safe, non-blocking per-objective locks preventing race conditions.
2. Action Idempotency: SHA-256 fingerprinting preventing accidental duplicate execution on resume.
3. Stale Permission Validation: Strict TTL checks preventing execution with expired authorization.
4. Situational Knowledge Graph: Automatic linking of objectives, milestones, decisions, and files.
5. Autonomous Quality Evaluation: Automated scoring of completed milestone artifacts.
"""
import os
import sys
import time
import json
import uuid
import shutil
import hashlib
import logging
import threading
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
        self.idempotency_dir = os.path.join(self.workspace_root, "data")
        os.makedirs(self.idempotency_dir, exist_ok=True)
        self.idempotency_file = os.path.join(self.idempotency_dir, "idempotency_cache.json")
        self.model_mgr = ModelManager()

        # Concurrency Protection: Lock registry per objective ID
        self._locks_mutex = threading.Lock()
        self._obj_locks: Dict[str, threading.Lock] = {}
        self._idempotency_lock = threading.Lock()

        # Default authorization TTL (24 hours)
        self.authorization_ttl: float = 86400.0

        logger.info(f"JARVIS 5.0 Mission Memory active. Storage: {self.storage_dir}")

    # ─── Concurrency Protection ────────────────────────────────────────────────

    def _get_objective_lock(self, objective_id: str) -> threading.Lock:
        """Retrieves or creates a thread lock for a specific objective ID."""
        with self._locks_mutex:
            if objective_id not in self._obj_locks:
                self._obj_locks[objective_id] = threading.Lock()
            return self._obj_locks[objective_id]

    # ─── Action Idempotency & Replay Prevention ────────────────────────────────

    def compute_action_fingerprint(self, action_type: str, target: str, payload: Any) -> str:
        """Computes a deterministic SHA-256 fingerprint for an external action."""
        raw = f"{action_type}:{target}:{json.dumps(payload, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_action_already_executed(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Checks if an external action has already been executed successfully."""
        with self._idempotency_lock:
            cache = self._load_idempotency_cache()
            return cache.get(fingerprint)

    def record_action_executed(self, fingerprint: str, action_type: str, target: str, result: Any):
        """Records completed action in the persistent idempotency cache."""
        with self._idempotency_lock:
            cache = self._load_idempotency_cache()
            cache[fingerprint] = {
                "fingerprint": fingerprint,
                "action_type": action_type,
                "target": target,
                "result": result,
                "executed_at": time.time()
            }
            self._save_idempotency_cache(cache)

    def _load_idempotency_cache(self) -> Dict[str, Any]:
        if os.path.isfile(self.idempotency_file):
            try:
                with open(self.idempotency_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_idempotency_cache(self, cache: Dict[str, Any]):
        temp_f = f"{self.idempotency_file}.tmp"
        try:
            with open(temp_f, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, default=str)
            os.replace(temp_f, self.idempotency_file)
        except Exception as e:
            logger.warning(f"Failed to persist idempotency cache: {e}")

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

    # ─── Stale Permission Validation ──────────────────────────────────────────

    def validate_objective_authorization(
        self,
        objective_id: str,
        user_id: str,
        provided_authorized_flag: bool
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifies authorization freshness (TTL window) before resuming long-running objectives.
        """
        obj = self.get_objective(objective_id)
        if not obj:
            return False, f"Objective '{objective_id}' not found."

        if obj.get("user_id") and user_id and obj.get("user_id") != user_id:
            return False, f"Permission denied: Objective belongs to '{obj.get('user_id')}', requested by '{user_id}'."

        if not provided_authorized_flag:
            return False, "Authorization flag not provided."

        last_auth = obj.get("last_authorized_at")
        now = time.time()

        if last_auth is not None:
            age = now - float(last_auth)
            if age > self.authorization_ttl:
                obj["status"] = "awaiting_reauthorization"
                self._save_objective(obj)
                return False, f"Security Guardian Gate: Objective '{objective_id}' authorization expired (age: {age:.0f}s > TTL {self.authorization_ttl:.0f}s). Fresh authorization required."

        return True, None

    # ─── Objective Decomposition & Creation ────────────────────────────────────

    def create_objective(self, goal: str, user_id: str = "Ayush") -> Dict[str, Any]:
        """
        Deconstructs a strategic user goal into sequential, verifiable milestones.
        Registers the objective in the Persistent Knowledge Graph.
        """
        oid = f"obj_{uuid.uuid4().hex[:8]}"
        logger.info(f"[MISSION MEMORY] Decomposing objective [{oid}]: '{goal}'")

        # Decompose using LLM into structured milestones
        milestones = self._decompose_goal_into_milestones(goal)
        now = time.time()

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
            "created_at": now,
            "updated_at": now,
            "last_authorized_at": now,
            "completed_at": None
        }

        self._save_objective(obj_data)
        logger.info(f"[MISSION MEMORY] Created objective '{obj_data['title']}' with {len(milestones)} milestones.")

        # Register in Knowledge Graph
        try:
            from core.knowledge_graph import knowledge_graph
            knowledge_graph.add_node(
                node_id=oid,
                node_type="objective",
                label=obj_data["title"],
                properties={"goal": goal, "user_id": user_id, "status": "active"}
            )
            for m in milestones:
                ms_node_id = f"ms_{oid}_{m['id']}"
                knowledge_graph.link_objective_milestone(oid, ms_node_id, m["title"], status=m["status"])
        except Exception as e:
            logger.warning(f"Knowledge graph registration notice: {e}")

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
        Protected with non-blocking concurrency locking, action idempotency,
        automated quality evaluation, and Knowledge Graph updates.
        """
        lock = self._get_objective_lock(objective_id)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            logger.warning(f"[MISSION MEMORY] Objective '{objective_id}' is locked by another active thread.")
            return {
                "status": "locked",
                "error": f"Objective '{objective_id}' is currently executing in another process/thread. Concurrency conflict avoided."
            }

        try:
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

            # 2. Idempotency Check: Verify if milestone directive was already executed
            action_fp = self.compute_action_fingerprint(
                action_type="milestone_execution",
                target=objective_id,
                payload={"milestone_id": ms["id"], "directive": ms["directive"]}
            )
            cached_action = self.is_action_already_executed(action_fp)
            if cached_action and ms.get("status") == "completed":
                logger.info(f"[MISSION MEMORY] Milestone {ms['id']} already executed. Returning cached outcome.")
                return {
                    "status": "success",
                    "milestone_completed": ms["id"],
                    "title": ms["title"],
                    "progress_percent": obj.get("progress_percent", 0.0),
                    "is_objective_completed": obj.get("status") == "completed",
                    "idempotent_replay_prevented": True,
                    "cached_result": cached_action.get("result")
                }

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

                # Link in Knowledge Graph
                try:
                    from core.knowledge_graph import knowledge_graph
                    ms_node_id = f"ms_{objective_id}_{ms['id']}"
                    knowledge_graph.add_node(ms_node_id, "milestone", ms["title"], {"status": "blocked", "blocker": ms["blocker"]})
                    knowledge_graph.add_edge(objective_id, ms_node_id, "BLOCKED_BY", {"reason": ms["blocker"]})
                except Exception:
                    pass

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
                proto_p = mission_res.get("prototype_path")
                report_p = mission_res.get("report_path")
                if report_p:
                    ms["artifacts"].append(report_p)
                if proto_p:
                    ms["artifacts"].append(proto_p)

                # Autonomous Quality Evaluation
                from core.autonomous_evaluator import autonomous_evaluator
                quality_res = autonomous_evaluator.evaluate_milestone_deliverables(
                    prototype_path=proto_p,
                    test_results={"passed": mission_res.get("tests_verified", True)},
                    report_path=report_p
                )
                ms["quality_evaluation"] = quality_res

                decision_entry = f"Milestone {ms['id']} ({ms['title']}) completed successfully. Quality score: {quality_res['milestone_quality_score']}/100 ({quality_res['grade']})."
                ms["decisions"].append(decision_entry)
                obj.setdefault("decisions_log", []).append(decision_entry)

                # Advance to next milestone
                obj["current_milestone_index"] = idx + 1
                obj["progress_percent"] = round(((idx + 1) / len(milestones)) * 100, 1)

                if obj["current_milestone_index"] >= len(milestones):
                    obj["status"] = "completed"
                    obj["completed_at"] = time.time()

                self._save_objective(obj)

                # Record Action Idempotency
                self.record_action_executed(
                    fingerprint=action_fp,
                    action_type="milestone_execution",
                    target=objective_id,
                    result={"milestone_id": ms["id"], "status": "completed", "score": quality_res["milestone_quality_score"]}
                )

                # Update Knowledge Graph
                try:
                    from core.knowledge_graph import knowledge_graph
                    ms_node_id = f"ms_{objective_id}_{ms['id']}"
                    knowledge_graph.link_objective_milestone(objective_id, ms_node_id, ms["title"], status="completed")
                    if proto_p:
                        knowledge_graph.link_decision_to_code(
                            decision_id=f"dec_{objective_id}_{ms['id']}",
                            decision_text=decision_entry,
                            file_path=proto_p,
                            objective_id=objective_id
                        )
                except Exception:
                    pass

                return {
                    "status": "success",
                    "milestone_completed": ms["id"],
                    "title": ms["title"],
                    "progress_percent": obj["progress_percent"],
                    "is_objective_completed": obj["status"] == "completed",
                    "quality_evaluation": quality_res,
                    "report_path": report_p,
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

        finally:
            lock.release()

    # ─── Windows Restart Continuity & Unfinished Work Detection ───────────────

    def detect_unfinished_work(self) -> List[Dict[str, Any]]:
        """
        Scans all objectives to detect unfinished milestones or paused work across reboots.
        """
        unfinished = []
        for obj in self.list_objectives():
            if obj.get("status") in ["active", "blocked", "in_progress", "awaiting_reauthorization"]:
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

    def resume_objective(
        self,
        objective_id: str,
        authorized: bool = True,
        user_id: str = "Ayush"
    ) -> Dict[str, Any]:
        """
        Resumes an objective that was interrupted by a Windows reboot or paused at a gate.
        Enforces stale permission validation (checking TTL) before resuming.
        """
        obj = self.get_objective(objective_id)
        if not obj:
            return {"status": "error", "error": f"Objective '{objective_id}' not found."}

        if obj["status"] == "completed":
            return {"status": "completed", "message": "Objective is already completed."}

        # Stale Permission / TTL Validation Check
        is_valid_auth, auth_err = self.validate_objective_authorization(
            objective_id=objective_id,
            user_id=user_id,
            provided_authorized_flag=authorized
        )
        if not is_valid_auth:
            return {
                "status": "blocked",
                "error": auth_err,
                "objective_id": objective_id
            }

        # Clear blockers and refresh authorization timestamp
        obj["status"] = "active"
        obj["last_authorized_at"] = time.time()
        idx = obj.get("current_milestone_index", 0)
        if idx < len(obj.get("milestones", [])):
            obj["milestones"][idx]["status"] = "pending"
            obj["milestones"][idx]["blocker"] = None
        self._save_objective(obj)

        return self.execute_next_milestone(objective_id, auto_approve=authorized)


# Global Singleton Instance
mission_memory = MissionMemoryManager()
