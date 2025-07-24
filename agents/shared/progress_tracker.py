"""Progress tracking for assessment flow"""
import json
import asyncio
from typing import Optional

class ProgressTracker:
    def __init__(self, websocket=None):
        self.websocket = websocket
        
    async def agent_active(self, agent_id: str, task: str):
        """Agent starts processing"""
        if self.websocket:
            await self.websocket.send_text(json.dumps({
                "type": "agent_active",
                "agent_id": agent_id,
                "task": task
            }))
    
    async def agent_complete(self, agent_id: str, content: str):
        """Agent completes with results"""
        if self.websocket:
            await self.websocket.send_text(json.dumps({
                "type": "agent_complete", 
                "agent_id": agent_id,
                "content": content[:500]  # Truncate for display
            }))
    
    async def connection_flow(self, from_agent: str, to_agent: str, action: str):
        """Data flows between agents"""
        if self.websocket:
            await self.websocket.send_text(json.dumps({
                "type": "connection_flow",
                "from_agent": from_agent,
                "to_agent": to_agent,
                "action": action
            }))
    
    async def content_stream(self, agent_id: str, content: str):
        """Stream content from agent"""
        if self.websocket:
            await self.websocket.send_text(json.dumps({
                "type": "content_stream",
                "agent_id": agent_id,
                "content": content
            }))