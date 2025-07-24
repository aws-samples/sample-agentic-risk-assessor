import asyncio
import random

async def retry_with_backoff(func, max_attempts=3, backoff_base=2.0):
    """Retry function with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            
            wait_time = backoff_base ** attempt + random.uniform(0, 1)
            await asyncio.sleep(wait_time)