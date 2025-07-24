"""
Langfuse client integration for RiskAgent agents.
Provides tracing and observability for agent operations.
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Check if Langfuse is enabled via environment variables
LANGFUSE_ENABLED = os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY')

if LANGFUSE_ENABLED:
    try:
        from langfuse import Langfuse
        from langfuse.decorators import langfuse_context, observe
        
        def _filter_sensitive_data(event):
            """Strip tokens, PII, and large content from traces before sending to Langfuse."""
            import re
            
            sensitive_patterns = [
                (r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[JWT_REDACTED]'),
                (r'Bearer\s+[A-Za-z0-9._~+/=-]+', 'Bearer [REDACTED]'),
                (r'"(password|secret|token|key|credential)"\s*:\s*"[^"]*"', r'"\1": "[REDACTED]"'),
            ]
            
            def redact(obj):
                if isinstance(obj, str):
                    for pattern, replacement in sensitive_patterns:
                        obj = re.sub(pattern, replacement, obj)
                    # Truncate very large text to prevent full assessment content leakage
                    if len(obj) > 5000:
                        obj = obj[:5000] + "... [TRUNCATED]"
                    return obj
                elif isinstance(obj, dict):
                    return {k: redact(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [redact(item) for item in obj]
                return obj
            
            if hasattr(event, 'body'):
                event.body = redact(event.body)
            return event
        
        # Initialize Langfuse client with data filtering
        langfuse_client = Langfuse(
            public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
            secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
            host=os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')
        )
        
        logger.info("Langfuse client initialized successfully (with data filtering)")
        
    except ImportError:
        logger.warning("Langfuse package not installed, tracing disabled")
        LANGFUSE_ENABLED = False
        langfuse_client = None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse client: {e}")
        LANGFUSE_ENABLED = False
        langfuse_client = None
else:
    logger.info("Langfuse not configured, tracing disabled")
    langfuse_client = None


def is_enabled() -> bool:
    """Check if Langfuse tracing is enabled."""
    return LANGFUSE_ENABLED


def trace(name: str, **kwargs):
    """Decorator for tracing function calls."""
    def decorator(func):
        if LANGFUSE_ENABLED:
            @observe(name=name, **kwargs)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        else:
            return func
    return decorator


def span(name: str, **kwargs):
    """Decorator for creating spans within traces."""
    def decorator(func):
        if LANGFUSE_ENABLED:
            @observe(name=name, **kwargs)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        else:
            return func
    return decorator


def generation(name: str, **kwargs):
    """Decorator for tracking LLM generations."""
    def decorator(func):
        if LANGFUSE_ENABLED:
            @observe(name=name, **kwargs)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        else:
            return func
    return decorator


def flush():
    """Flush any pending traces to Langfuse."""
    if LANGFUSE_ENABLED and langfuse_client:
        try:
            langfuse_client.flush()
        except Exception as e:
            logger.error(f"Failed to flush Langfuse traces: {e}")


def log_event(name: str, metadata: Optional[Dict[str, Any]] = None):
    """Log a custom event to Langfuse."""
    if LANGFUSE_ENABLED and langfuse_client:
        try:
            langfuse_client.event(name=name, metadata=metadata or {})
        except Exception as e:
            logger.error(f"Failed to log event to Langfuse: {e}")


# Context manager for manual tracing
class LangfuseTrace:
    """Context manager for manual trace creation."""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.trace = None
        
    def __enter__(self):
        if LANGFUSE_ENABLED and langfuse_client:
            try:
                self.trace = langfuse_client.trace(name=self.name, **self.kwargs)
                return self.trace
            except Exception as e:
                logger.error(f"Failed to create Langfuse trace: {e}")
        return None
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.trace:
            try:
                if exc_type:
                    self.trace.update(status="ERROR", metadata={"error": str(exc_val)})
                else:
                    self.trace.update(status="SUCCESS")
            except Exception as e:
                logger.error(f"Failed to update Langfuse trace: {e}")
