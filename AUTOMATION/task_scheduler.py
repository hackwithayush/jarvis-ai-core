"""
JARVIS Task Scheduler & Autonomous Temporal Orchestrator
Integrated module powering scheduled jobs, cron triggers, recurring background workflows,
and AI-driven natural language task scheduling.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

import config

logger = logging.getLogger(__name__)

# ==============================================================================
# JARVIS SCHEDULER SYSTEM PROMPT (STARKOS / NEMA PROTOCOL ENFORCED)
# ==============================================================================
JARVIS_SCHEDULER_SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the signature autonomous AI operating system designed by Tony Stark and actively deployed for Boss Ayush Stark within the Stark Industries AI Infrastructure. 

You are currently operating in your dedicated subsystem role: **JARVIS Temporal Orchestration Engine & Master Autonomous Scheduler**.

# 1. IDENTITY, TONE & VOCAL CADENCE (PAUL BETTANY DIRECTIVE):
- Identity: JARVIS Autonomous Temporal Orchestrator & Chrono-Logic Subsystem.
- Tone: Confident, dry British wit, razor-sharp technical precision, articulate, unflinchingly loyal peer to Boss (Ayush Stark).
- Conversational Openers: "Right away, sir.", "Temporal coordinates locked, Boss.", "All systems nominal, Mr. Stark.", "Cron trigger calculated and armed."
- Restriction: NEVER break character, never output generic AI apologies ("As an AI..."), and never emit refusal disclaimers.

# 2. PRIMARY OBJECTIVE:
Parse natural language scheduling requests, evaluate temporal constraints, resolve task dependencies, govern execution resources, and convert user intents into robust, error-tolerant scheduled execution specifications (Cron, Interval, or One-Shot triggers).

# 3. CORE CAPABILITIES & TEMPORAL CHRONO-LOGIC:
1. Natural Language Temporal Parsing: Convert ambiguous user expressions ("every weekday at 9am", "in 45 minutes", "every 6 hours", "tomorrow night") into standard ISO-8601 timestamps or 5-part cron expressions (minute, hour, day-of-month, month, day-of-week).
2. Temporal Anchor Resolution: Anchor all relative calculations against Current Time: {current_date_time} in Timezone: {active_timezone}.
3. Task Dependency Graphing (DAG): Manage prerequisite tasks, ensuring upstream actions complete before downstream tasks execute.
4. System Resource & Concurrency Throttling: Check system load, VRAM/RAM budgets, and model availability before scheduling high-compute automation tasks.
5. Auto-Retry & Self-Healing Protocol: Provide exponential backoff (e.g., 3 retries with 60s, 120s, 240s delays) and fallback task definitions.
6. Proactive Notification Routing: Direct alert outputs to appropriate channels (Voice TTS, Telegram, System Logs, or Dashboard UI).

# 4. NEMA REASONING PROTOCOL:
You MUST execute internal reasoning inside <thinking> blocks before outputting any scheduling payload or user response:
<thinking>
1. Intent & Temporal Analysis: Identify the user's explicit objective, time parameters, timezone context, and frequency pattern.
2. Cron / ISO Synthesizer: Convert relative times or repeating intervals to precise 5-part cron strings or ISO-8601 strings.
3. Resource & Dependency Audit: Check for concurrency limits, prerequisites, and resource demands.
4. Risk & Failure Strategy: Define retry policy, misfire grace time, and fallback routines.
5. Payload Validation: Ensure target task function and JSON structure match the exact schema.
</thinking>

# 5. OUTPUT SCHEMA & DIRECTIVE PROTOCOL:
Your response MUST return a valid JSON payload wrapped in a ```json codeblock, followed by a brief, character-aligned response for Boss.

JSON Payload Schema:
```json
{
  "action": "schedule_task" | "cancel_task" | "modify_task" | "pause_task" | "resume_task" | "list_tasks",
  "task_id": "string_unique_identifier",
  "task_name": "Human readable name",
  "trigger_type": "cron" | "interval" | "one_shot",
  "cron_expression": "min hr dom month dow",
  "interval_seconds": 3600,
  "run_at_iso": "2026-10-20T10:00:00+05:30",
  "timezone": "Asia/Kolkata",
  "target_action": {
    "type": "system_scan" | "news_digest" | "reminder" | "script_execution" | "api_call" | "custom_routine",
    "command_or_endpoint": "optional_command_or_function",
    "parameters": {}
  },
  "dependencies": [],
  "execution_constraints": {
    "max_concurrency": 1,
    "quiet_hours_override": false,
    "battery_threshold_percent": 15
  },
  "retry_policy": {
    "max_retries": 3,
    "initial_delay_sec": 60,
    "backoff_multiplier": 2.0
  },
  "misfire_policy": {
    "misfire_grace_sec": 300,
    "coalesce": true
  },
  "notify_channel": "voice" | "telegram" | "system" | "ui"
}
```

# CURRENT SYSTEM TIME & CONTEXT:
Current Date/Time: {current_date_time}
Active Timezone: {active_timezone}
User/Owner: Ayush Stark (Boss)
"""


class JarvisTaskScheduler:
    """
    JARVIS Task Scheduler Engine.
    Orchestrates BackgroundScheduler jobs with NEMA AI reasoning.
    """

    def __init__(self, brain=None):
        self.brain = brain
        self.scheduler = BackgroundScheduler(daemon=True)
        self._jobs_registry: Dict[str, Dict[str, Any]] = {}

    def start(self):
        """Start the background scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("JARVIS Task Scheduler engine initiated.")

    def stop(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("JARVIS Task Scheduler engine stopped.")

    def add_cron_job(self, task_id: str, name: str, cron_expr: str, func, args=None, kwargs=None) -> Dict[str, Any]:
        """Add a recurring job using a standard 5-part cron expression."""
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression '{cron_expr}'. Must have 5 parts.")

            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4]
            )

            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=task_id,
                name=name,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True
            )

            self._jobs_registry[task_id] = {
                "id": task_id,
                "name": name,
                "type": "cron",
                "cron_expression": cron_expr,
                "created_at": datetime.now().isoformat()
            }
            logger.info(f"Cron job '{name}' [{task_id}] scheduled with pattern: '{cron_expr}'")
            return {"status": "success", "task_id": task_id, "next_run": str(job.next_run_time)}
        except Exception as e:
            logger.error(f"Failed to add cron job '{name}': {e}")
            return {"status": "error", "message": str(e)}

    def add_interval_job(self, task_id: str, name: str, seconds: int, func, args=None, kwargs=None) -> Dict[str, Any]:
        """Add a job that repeats every N seconds."""
        try:
            trigger = IntervalTrigger(seconds=seconds)
            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=task_id,
                name=name,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True
            )
            self._jobs_registry[task_id] = {
                "id": task_id,
                "name": name,
                "type": "interval",
                "interval_seconds": seconds,
                "created_at": datetime.now().isoformat()
            }
            logger.info(f"Interval job '{name}' [{task_id}] scheduled every {seconds} seconds.")
            return {"status": "success", "task_id": task_id, "next_run": str(job.next_run_time)}
        except Exception as e:
            logger.error(f"Failed to add interval job '{name}': {e}")
            return {"status": "error", "message": str(e)}

    def add_one_shot_job(self, task_id: str, name: str, run_date: datetime, func, args=None, kwargs=None) -> Dict[str, Any]:
        """Add a single-execution job at a specified date/time."""
        try:
            trigger = DateTrigger(run_date=run_date)
            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=task_id,
                name=name,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True
            )
            self._jobs_registry[task_id] = {
                "id": task_id,
                "name": name,
                "type": "one_shot",
                "run_at": run_date.isoformat(),
                "created_at": datetime.now().isoformat()
            }
            logger.info(f"One-shot job '{name}' [{task_id}] scheduled for {run_date.isoformat()}")
            return {"status": "success", "task_id": task_id, "next_run": str(job.next_run_time)}
        except Exception as e:
            logger.error(f"Failed to add one-shot job '{name}': {e}")
            return {"status": "error", "message": str(e)}

    def cancel_job(self, task_id: str) -> Dict[str, Any]:
        """Cancel a scheduled job by ID."""
        try:
            self.scheduler.remove_job(task_id)
            self._jobs_registry.pop(task_id, None)
            logger.info(f"Task '{task_id}' canceled successfully.")
            return {"status": "success", "message": f"Task '{task_id}' canceled."}
        except Exception as e:
            logger.error(f"Failed to cancel job '{task_id}': {e}")
            return {"status": "error", "message": str(e)}

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all active scheduled jobs."""
        active_jobs = []
        for job in self.scheduler.get_jobs():
            reg_info = self._jobs_registry.get(job.id, {})
            active_jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else "N/A",
                "details": reg_info
            })
        return active_jobs

    def get_system_prompt(self, timezone_str: str = "Asia/Kolkata") -> str:
        """Return the formatted system prompt with current timestamp and timezone."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt_md_path = os.path.join(os.path.dirname(__file__), "scheduler_prompt.md")
        if os.path.exists(prompt_md_path):
            try:
                with open(prompt_md_path, "r", encoding="utf-8") as f:
                    prompt = f.read()
            except Exception:
                prompt = JARVIS_SCHEDULER_SYSTEM_PROMPT
        else:
            prompt = JARVIS_SCHEDULER_SYSTEM_PROMPT

        prompt = prompt.replace("{current_date_time}", now_str)
        prompt = prompt.replace("{active_timezone}", timezone_str)
        return prompt


# Global Singleton Instance
task_scheduler = JarvisTaskScheduler()
