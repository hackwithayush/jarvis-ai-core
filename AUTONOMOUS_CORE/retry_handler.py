"""
Retry Handler
Provides robust fallback and retry logic for API timeouts and model crashes.
"""
import time
from functools import wraps

def with_retry(max_retries=3, delay=2):
    """ Decorator to seamlessly retry an execution step if a tool or API fails. """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    print(f"[RETRY HANDLER] Error: {e}. Retrying ({attempts}/{max_retries}) in {delay}s...")
                    time.sleep(delay)
            print(f"[RETRY HANDLER] CRITICAL: Task failed completely after {max_retries} attempts.")
            return f"ERROR: Step execution failed after {max_retries} attempts."
        return wrapper
    return decorator
