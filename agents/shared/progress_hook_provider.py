"""Strands hook provider for detailed progress tracking"""
import json
import asyncio
import logging
from typing import Any
from strands.hooks import HookProvider, HookRegistry
from strands.experimental.hooks.events import (
    BeforeToolInvocationEvent, 
    AfterToolInvocationEvent,
    BeforeModelInvocationEvent,
    AfterModelInvocationEvent
)
from strands.hooks.events import (
    BeforeInvocationEvent,
    AfterInvocationEvent
)

logger = logging.getLogger(__name__)

class ProgressHookProvider:
    """Hook provider for detailed agent lifecycle progress tracking"""
    
    def __init__(self, websocket=None, agent_name: str = "unknown"):
        self.websocket = websocket
        self.agent_name = agent_name
    
    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register progress tracking hooks"""
        registry.add_callback(BeforeInvocationEvent, self.on_before_invocation)
        registry.add_callback(AfterInvocationEvent, self.on_after_invocation)
        registry.add_callback(BeforeToolInvocationEvent, self.on_before_tool)
        registry.add_callback(AfterToolInvocationEvent, self.on_after_tool)
        registry.add_callback(BeforeModelInvocationEvent, self.on_before_model)
        registry.add_callback(AfterModelInvocationEvent, self.on_after_model)
    
    def on_before_invocation(self, event: BeforeInvocationEvent) -> None:
        """Agent request starts"""
        self._send_progress_event({
            "type": "agent_active",
            "agent_id": self.agent_name,
            "task": "Processing request"
        })
    
    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        """Agent request completes"""
        self._send_progress_event({
            "type": "agent_complete",
            "agent_id": self.agent_name,
            "content": "Request completed"
        })
    
    def on_before_tool(self, event: BeforeToolInvocationEvent) -> None:
        """Tool execution starts"""
        tool_name = event.tool_use.name if event.tool_use else "Unknown tool"
        self._send_progress_event({
            "type": "tool_start",
            "agent_id": self.agent_name,
            "tool_name": tool_name,
            "description": f"Starting {tool_name}"
        })
    
    def on_after_tool(self, event: AfterToolInvocationEvent) -> None:
        """Tool execution completes"""
        tool_name = event.tool_use.name if event.tool_use else "Unknown tool"
        
        if event.exception:
            self._send_progress_event({
                "type": "tool_error",
                "agent_id": self.agent_name,
                "tool_name": tool_name,
                "error": str(event.exception)
            })
        else:
            self._send_progress_event({
                "type": "tool_complete",
                "agent_id": self.agent_name,
                "tool_name": tool_name,
                "result_summary": f"Completed {tool_name}"
            })
    
    def on_before_model(self, event: BeforeModelInvocationEvent) -> None:
        """Model invocation starts"""
        self._send_progress_event({
            "type": "status_update",
            "agent_id": self.agent_name,
            "status": "Thinking",
            "details": "Model processing"
        })
    
    def on_after_model(self, event: AfterModelInvocationEvent) -> None:
        """Model invocation completes"""
        if event.exception:
            self._send_progress_event({
                "type": "status_update",
                "agent_id": self.agent_name,
                "status": "Error",
                "details": f"Model error: {event.exception}"
            })
        else:
            self._send_progress_event({
                "type": "status_update",
                "agent_id": self.agent_name,
                "status": "Complete",
                "details": "Model response received"
            })
    
    def _send_progress_event(self, event_data: dict):
        """Send progress event to WebSocket"""
        if self.websocket:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._async_send(event_data))
                else:
                    loop.run_until_complete(self._async_send(event_data))
            except Exception as e:
                logger.warning(f"Failed to send hook progress event: {e}")
    
    async def _async_send(self, event_data: dict):
        """Async WebSocket send"""
        try:
            await self.websocket.send_text(json.dumps(event_data))
            logger.debug(f"Hook progress event sent: {event_data['type']} for {self.agent_name}")
        except Exception as e:
            logger.warning(f"Hook WebSocket send failed: {e}")