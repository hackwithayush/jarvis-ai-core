"""
Scheduler — Automated Knowledge Updates
Manages periodic news fetching and knowledge base maintenance.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from core.knowledge_manager import KnowledgeManager
from core.news_fetcher import NewsFetcher

logger = logging.getLogger(__name__)


class UpdateScheduler:
    """Manages scheduled tasks for automated knowledge updates."""

    def __init__(self, knowledge_manager: KnowledgeManager = None):
        self.scheduler = BackgroundScheduler(daemon=True)
        self.knowledge_manager = knowledge_manager or KnowledgeManager()
        self.news_fetcher = NewsFetcher()
        self._last_update = None
        self._last_update_status = "Never run"
        self._articles_added = 0
        self._is_updating = False

    def start(self):
        """Start the scheduler with configured jobs."""
        # News update job
        self.scheduler.add_job(
            func=self.update_knowledge,
            trigger=IntervalTrigger(hours=config.NEWS_UPDATE_INTERVAL_HOURS),
            id="news_update",
            name="Fetch and index news",
            replace_existing=True,
        )

        # Cleanup job — run daily
        self.scheduler.add_job(
            func=self.cleanup_old_knowledge,
            trigger=IntervalTrigger(days=1),
            id="knowledge_cleanup",
            name="Clean up old knowledge",
            replace_existing=True,
        )

        # Daily news digest — auto-task (runs at configured hour)
        from apscheduler.triggers.cron import CronTrigger
        self.scheduler.add_job(
            func=self.daily_news_digest,
            trigger=CronTrigger(hour=9, minute=0),  # 9 AM daily
            id="daily_digest",
            name="Daily AI news digest",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            f"Scheduler started. News updates every {config.NEWS_UPDATE_INTERVAL_HOURS}h, "
            f"cleanup daily, digest at 9AM."
        )

        # Initial fetch on start
        if config.INITIAL_FETCH_ON_START:
            logger.info("Running initial knowledge fetch...")
            self.scheduler.add_job(
                func=self.update_knowledge,
                id="initial_fetch",
                name="Initial news fetch",
                replace_existing=True,
            )

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped.")

    def update_knowledge(self):
        """Fetch news and update the knowledge base."""
        if self._is_updating:
            logger.info("Update already in progress, skipping.")
            return

        self._is_updating = True
        total_added = 0

        try:
            logger.info("Starting knowledge update...")

            # 1. Fetch RSS feeds
            articles = self.news_fetcher.fetch_all_feeds()
            logger.info(f"Fetched {len(articles)} articles from RSS feeds.")

            # 2. Add to knowledge base
            if articles:
                total_added += self.knowledge_manager.add_documents_batch(articles)

            # 3. Fetch Wikipedia current events
            try:
                wiki_events = self.news_fetcher.fetch_wikipedia_current_events()
                if wiki_events:
                    total_added += self.knowledge_manager.add_documents_batch(wiki_events)
                    logger.info(f"Added {len(wiki_events)} Wikipedia events.")
            except Exception as e:
                logger.warning(f"Wikipedia fetch failed: {e}")

            # Update status
            self._last_update = datetime.now(timezone.utc).isoformat()
            self._articles_added = total_added
            self._last_update_status = f"Success: {total_added} chunks added"
            logger.info(f"Knowledge update complete. {total_added} chunks added.")

            # Reset seen URLs for next cycle
            self.news_fetcher.reset_seen()

        except Exception as e:
            self._last_update_status = f"Error: {e}"
            logger.error(f"Knowledge update failed: {e}")
        finally:
            self._is_updating = False

    def cleanup_old_knowledge(self):
        """Remove outdated knowledge from the database."""
        try:
            removed = self.knowledge_manager.cleanup_old_knowledge()
            logger.info(f"Cleanup complete. Removed {removed} old chunks.")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    # ─── Auto-Tasks ─────────────────────────────────────────────────

    def daily_news_digest(self):
        """Auto-task: Generate and save a daily AI news digest."""
        import os
        try:
            logger.info("Running daily news digest auto-task...")

            # Use the web search engine to fetch latest news
            from core.web_search import WebSearchEngine
            search = WebSearchEngine()

            topics = ["artificial intelligence", "technology", "world news"]
            digest = f"# Daily News Digest — {datetime.now().strftime('%B %d, %Y')}\n\n"

            for topic in topics:
                digest += f"## {topic.title()}\n\n"
                try:
                    results = search.search_news(topic)
                    if results:
                        for r in results[:5]:
                            title = r.get("title", "")
                            source = r.get("source", "")
                            snippet = r.get("snippet", "")
                            digest += f"- **{title}**"
                            if source:
                                digest += f" ({source})"
                            digest += "\n"
                            if snippet:
                                digest += f"  {snippet[:150]}\n"
                            digest += "\n"
                    else:
                        digest += "- No results available\n\n"
                except Exception as e:
                    digest += f"- Error fetching: {e}\n\n"

            # Save digest to file
            digest_dir = os.path.join(config.DATA_DIR, "digests")
            os.makedirs(digest_dir, exist_ok=True)
            filename = f"digest_{datetime.now().strftime('%Y%m%d')}.md"
            filepath = os.path.join(digest_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(digest)

            logger.info(f"Daily digest saved: {filepath}")
            self._last_digest = filepath

        except Exception as e:
            logger.error(f"Daily digest failed: {e}")

    def schedule_custom_task(self, task_func, cron_expr: str, task_id: str, task_name: str):
        """Schedule a custom auto-task with a cron expression."""
        try:
            from apscheduler.triggers.cron import CronTrigger
            parts = cron_expr.split()
            trigger = CronTrigger(
                minute=parts[0] if len(parts) > 0 else '*',
                hour=parts[1] if len(parts) > 1 else '*',
                day=parts[2] if len(parts) > 2 else '*',
                month=parts[3] if len(parts) > 3 else '*',
                day_of_week=parts[4] if len(parts) > 4 else '*',
            )
            self.scheduler.add_job(
                func=task_func,
                trigger=trigger,
                id=task_id,
                name=task_name,
                replace_existing=True,
            )
            logger.info(f"Custom task scheduled: {task_name} ({cron_expr})")
            return {"status": "ok", "message": f"Task '{task_name}' scheduled."}
        except Exception as e:
            logger.error(f"Failed to schedule task: {e}")
            return {"status": "error", "message": str(e)}

    def get_status(self) -> dict:
        """Get scheduler status."""
        kb_stats = self.knowledge_manager.get_stats()

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else "N/A",
            })

        return {
            "scheduler_running": self.scheduler.running,
            "is_updating": self._is_updating,
            "last_update": self._last_update,
            "last_status": self._last_update_status,
            "articles_added_last": self._articles_added,
            "scheduled_jobs": jobs,
            "knowledge_base": kb_stats,
            "update_interval_hours": config.NEWS_UPDATE_INTERVAL_HOURS,
        }

    def trigger_manual_update(self):
        """Trigger an immediate knowledge update."""
        if self._is_updating:
            return {"status": "error", "message": "Update already in progress"}

        self.scheduler.add_job(
            func=self.update_knowledge,
            id="manual_update",
            name="Manual news update",
            replace_existing=True,
        )
        return {"status": "ok", "message": "Manual update triggered"}
