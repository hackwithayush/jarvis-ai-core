import asyncio
import logging

logger = logging.getLogger(__name__)

def run_async(coro):
    """
    Universal async runner that safely executes coroutines in both 
    synchronous and already-running async environments.
    """
    try:
        # 1. Try to get the running event loop
        loop = asyncio.get_running_loop()
        # If we are here, there's already a loop running.
        # Check if it's already running a task
        if loop.is_running():
            # In a running loop (like during a Flask request or Telegram handler),
            # we can't use run_until_complete. We could use a thread, 
            # but for simple coros we can sometimes use nested loops if supported,
            # or just ensure we aren't blocking.
            # However, Flask/Telegram are often sync-blocking in our context.
            # The safest way to run a coro from a sync function INSIDE an async loop
            # is typically not easy without nesting.
            # For this project, we prioritize reliability:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # 2. No loop is running, create a new one
        return asyncio.run(coro)
    except Exception as e:
        logger.error(f"Async runner error: {e}")
        raise e
