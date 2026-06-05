"""
Utility Functions — Production-Grade Resilience
Contains helpers for retries, safe parsing, and error recovery.
"""
import json
import re
import logging
import asyncio
import functools
from typing import Any, Callable, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar("T")

def retry(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying async functions on failure.
    """
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_retries = 0
            current_delay = delay
            
            while current_retries <= retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    current_retries += 1
                    if current_retries > retries:
                        logger.error(f"Retry limit reached for {func.__name__}: {e}")
                        raise e
                    
                    logger.warning(f"Retrying {func.__name__} ({current_retries}/{retries}) after {current_delay}s... Error: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

def retry_sync(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying synchronous functions on failure.
    """
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_retries = 0
            current_delay = delay
            
            while current_retries <= retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    current_retries += 1
                    import time
                    if current_retries > retries:
                        logger.error(f"Retry limit reached for {func.__name__}: {e}")
                        raise e
                    
                    logger.warning(f"Retrying {func.__name__} ({current_retries}/{retries}) after {current_delay}s... Error: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

def safe_json_parse(text: str, fallback: Any = None) -> Any:
    """
    Extract and parse JSON from messy AI output using regex.
    """
    if not text:
        return fallback
        
    try:
        # 1. Direct parse attempt
        return json.loads(text.strip())
    except json.JSONDecodeError:
        try:
            # 2. Extract block between curly braces
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
            
    logger.warning(f"Failed to parse JSON from response. Falling back to default.")
    return fallback
