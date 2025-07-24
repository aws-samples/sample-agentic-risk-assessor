import asyncio
import json
import logging
from typing import Optional, Any, Dict
from strands.core.callback_handler import CallbackHandler

logger = logging.getLogger(__name__)

class UnifiedCallbackHandler(CallbackHandler):
    """Unified callback handler that sends to both streaming and progress WebSockets"""
    
    def __init__(self, streaming_websocket=None, progress_tracker=None):
        super().__init__()
        self.streaming_websocket = streaming_websocket
        self.progress_tracker = progress_tracker
    
    async def on_agent_start(self, agent_name: str, inputs: Dict[str, Any], **kwargs) -> None:
        # Send to progress tracker
        if self.progress_tracker:
            await self.progress_tracker.update_progress(
                agent_name, "started", f"Agent {agent_name} started", 0
            )
    
    async def on_agent_end(self, agent_name: str, outputs: Dict[str, Any], **kwargs) -> None:
        # Send to progress tracker
        if self.progress_tracker:
            await self.progress_tracker.update_progress(
                agent_name, "completed", f"Agent {agent_name} completed", 100
            )
    
    async def on_agent_error(self, agent_name: str, error: Exception, **kwargs) -> None:
        # Send to progress tracker
        if self.progress_tracker:
            await self.progress_tracker.update_progress(
                agent_name, "error", f"Agent {agent_name} error: {str(error)}", 0
            )
    
    async def on_tool_start(self, tool_name: str, inputs: Dict[str, Any], **kwargs) -> None:
        # Send to progress tracker
        if self.progress_tracker:
            await self.progress_tracker.update_progress(
                "current", "processing", f"Using tool: {tool_name}", None
            )
    
    async def on_tool_end(self, tool_name: str, outputs: Dict[str, Any], **kwargs) -> None:
        # Send to progress tracker
        if self.progress_tracker:
            await self.progress_tracker.update_progress(
                "current", "processing", f"Tool {tool_name} completed", None
            )
    
    async def on_llm_start(self, prompts: list, **kwargs) -> None:
        # Send to progress tracker
        if self.progress_tracker:
            await self.progress_tracker.update_progress(
                "current", "thinking", "Processing request...", None
            )
    
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        # Send to streaming WebSocket in Strands format
        if self.streaming_websocket:
            try:
                await self.streaming_websocket.send_json({
                    "type": "stream",
                    "data": token,
                    "status": "streaming"
                })
            except Exception as e:
                logger.error(f"Error sending token to streaming WebSocket: {e}")
    
    async def on_llm_end(self, response: Any, **kwargs) -> None:
        # Send completion to streaming WebSocket
        if self.streaming_websocket:
            try:
                await self.streaming_websocket.send_json({
                    "type": "complete",
                    "response": str(response),
                    "status": "complete",
                    "agent": "risk_assessment"
                })
            except Exception as e:
                logger.error(f"Error sending completion to streaming WebSocket: {e}")