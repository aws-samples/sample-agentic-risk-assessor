"""Strands-native progress callback handler for WebSocket progress updates"""
import json
import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class ProgressCallbackHandler:
    """Strands callback handler that sends progress events to WebSocket"""
    
    def __init__(self, websocket=None, agent_name: str = "unknown"):
        self.websocket = websocket
        self.agent_name = agent_name
        self.current_tool = None
        
    def __call__(self, **kwargs: Any) -> None:
        """Handle Strands callback events and convert to WebSocket progress events"""
        try:
            # Extract callback data
            reasoning_text = kwargs.get("reasoningText", "")
            data = kwargs.get("data", "")
            complete = kwargs.get("complete", False)
            current_tool_use = kwargs.get("current_tool_use", {})
            
            # Handle tool execution events
            if current_tool_use and current_tool_use.get("name"):
                tool_name = current_tool_use.get("name", "Unknown tool")
                if self.current_tool != tool_name:
                    # New tool started
                    self.current_tool = tool_name
                    self._send_progress_event({
                        "type": "agent_active",
                        "agent_id": self.agent_name,
                        "task": f"Using {tool_name}"
                    })
            
            # Handle streaming content
            if data:
                self._send_progress_event({
                    "type": "content_stream",
                    "agent_id": self.agent_name,
                    "content": data
                })
            
            # Handle completion
            if complete:
                if self.current_tool:
                    self._send_progress_event({
                        "type": "agent_complete",
                        "agent_id": self.agent_name,
                        "content": f"Completed {self.current_tool}"
                    })
                    self.current_tool = None
                else:
                    self._send_progress_event({
                        "type": "agent_complete",
                        "agent_id": self.agent_name,
                        "content": "Processing complete"
                    })
                    
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")
    
    def _send_progress_event(self, event_data: dict):
        """Send progress event to WebSocket"""
        if self.websocket:
            try:
                # Try async send first
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._async_send(event_data))
                else:
                    loop.run_until_complete(self._async_send(event_data))
            except Exception as e:
                logger.warning(f"Failed to send progress event: {e}")
    
    async def _async_send(self, event_data: dict):
        """Async WebSocket send"""
        try:
            await self.websocket.send_text(json.dumps(event_data))
            logger.debug(f"Progress event sent: {event_data['type']} for {self.agent_name}")
        except Exception as e:
            logger.warning(f"WebSocket send failed: {e}")