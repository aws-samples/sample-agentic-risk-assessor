"""
Optimized logging configuration for agents to prevent large files in CloudWatch
"""
import logging
import json
import sys
from typing import Any, Dict

class CloudWatchOptimizedFormatter(logging.Formatter):
    """Custom formatter that truncates large content to prevent CloudWatch bloat"""
    
    MAX_MESSAGE_LENGTH = 1000  # Maximum characters per log message
    MAX_PARAGRAPH_LENGTH = 300  # Maximum characters for agent responses (one paragraph)
    MAX_DICT_ITEMS = 5  # Maximum items to show in dictionaries
    AGENT_RESPONSE_KEYS = ['response', 'result', 'content', 'body', 'fsi_review', 'assessment_content']
    
    def format(self, record):
        # Truncate the message if it's too long
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            if len(record.msg) > self.MAX_MESSAGE_LENGTH:
                record.msg = record.msg[:self.MAX_MESSAGE_LENGTH] + "... [TRUNCATED]"
        
        # Handle args that might contain large content
        if record.args:
            truncated_args = []
            for arg in record.args:
                truncated_args.append(self._truncate_content(arg))
            record.args = tuple(truncated_args)
        
        return super().format(record)
    
    def _truncate_content(self, content: Any, is_agent_response: bool = False) -> Any:
        """Truncate various types of content"""
        if isinstance(content, str):
            max_length = self.MAX_PARAGRAPH_LENGTH if is_agent_response else self.MAX_MESSAGE_LENGTH
            if len(content) > max_length:
                # For agent responses, try to end at sentence boundary
                if is_agent_response:
                    truncated = content[:max_length]
                    # Find last sentence ending
                    last_period = truncated.rfind('.')
                    last_newline = truncated.rfind('\n')
                    if last_period > max_length * 0.5:  # If we have a reasonable sentence
                        return truncated[:last_period + 1] + " [TRUNCATED - AGENT RESPONSE]"
                    elif last_newline > max_length * 0.3:  # Or paragraph break
                        return truncated[:last_newline] + " [TRUNCATED - AGENT RESPONSE]"
                return content[:max_length] + "... [TRUNCATED]"
            return content
        elif isinstance(content, dict):
            return self._truncate_dict(content)
        elif isinstance(content, list):
            return self._truncate_list(content)
        else:
            content_str = str(content)
            max_length = self.MAX_PARAGRAPH_LENGTH if is_agent_response else self.MAX_MESSAGE_LENGTH
            if len(content_str) > max_length:
                return content_str[:max_length] + "... [TRUNCATED]"
            return content
    
    def _truncate_dict(self, d: Dict) -> Dict:
        """Truncate dictionary content"""
        truncated = {}
        count = 0
        for key, value in d.items():
            if count >= self.MAX_DICT_ITEMS:
                truncated[f"... +{len(d) - count} more items"] = "[TRUNCATED]"
                break
            
            # Special handling for known large content keys
            is_agent_response = key.lower() in [k.lower() for k in self.AGENT_RESPONSE_KEYS]
            if is_agent_response:
                if isinstance(value, str) and len(value) > self.MAX_PARAGRAPH_LENGTH:
                    truncated[key] = self._truncate_content(value, is_agent_response=True)
                else:
                    truncated[key] = self._truncate_content(value, is_agent_response=True)
            else:
                truncated[key] = self._truncate_content(value)
            count += 1
        
        return truncated
    
    def _truncate_list(self, lst: list) -> list:
        """Truncate list content"""
        if len(lst) > self.MAX_DICT_ITEMS:
            truncated = lst[:self.MAX_DICT_ITEMS]
            truncated.append(f"... +{len(lst) - self.MAX_DICT_ITEMS} more items [TRUNCATED]")
            return truncated
        return [self._truncate_content(item) for item in lst]

class ContentFilter(logging.Filter):
    """Filter to prevent logging of sensitive content and ALL streaming results"""
    
    SENSITIVE_KEYS = ['password', 'token', 'key', 'secret', 'credential']
    STREAMING_PATTERNS = ['streaming', 'chunk', 'delta', 'stream_', 'event_loop', 'process_stream', 'stream_event', 'streaming_result', '[stream]', 'event:', 'tooluse', 'callback_handler', 'event_loop_cycle_id']
    
    def filter(self, record):
        message = str(record.getMessage())
        
        # Block sensitive information
        for key in self.SENSITIVE_KEYS:
            if key in message.lower():
                return False
        
        # Block ALL streaming-related messages at ANY level to prevent CloudWatch explosion
        for pattern in self.STREAMING_PATTERNS:
            if pattern in message.lower():
                return False
        
        return True

def setup_optimized_logging(logger_name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Setup optimized logging configuration for agents"""
    
    # Get or create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with optimized formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Add custom formatter and filter
    formatter = CloudWatchOptimizedFormatter(
        fmt="%(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(ContentFilter())
    
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def setup_strands_logging():
    """Setup optimized logging for Strands framework - WARNING level only to prevent CloudWatch bloat"""
    strands_logger = logging.getLogger("strands")
    strands_logger.setLevel(logging.WARNING)  # Only warnings and errors to prevent streaming spam
    
    # Remove existing handlers
    for handler in strands_logger.handlers[:]:
        strands_logger.removeHandler(handler)
    
    # Add optimized handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.WARNING)
    formatter = CloudWatchOptimizedFormatter(
        fmt="%(levelname)s | STRANDS | %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(ContentFilter())
    
    strands_logger.addHandler(handler)
    strands_logger.propagate = False
    
    return strands_logger