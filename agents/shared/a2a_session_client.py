#!/usr/bin/env python3
"""
A2A Session-Aware Client for inter-agent communication
"""
from strands.multiagent.a2a import A2AClient
from agents.shared.a2a_discovery import get_agent_urls
import logging

logger = logging.getLogger(__name__)

class A2ASessionClient:
    def __init__(self):
        """Initialize A2A client with agent discovery"""
        try:
            known_urls = get_agent_urls()
            self.client = A2AClient(known_agent_urls=known_urls)
            logger.info(f"A2A client initialized with URLs: {known_urls}")
        except Exception as e:
            logger.error(f"Failed to initialize A2A client: {e}")
            self.client = None
    
    async def invoke_agent(self, agent_name: str, message: str, session_id: str = None, user_id: str = None):
        """Invoke another agent with session context"""
        if not self.client:
            return f"A2A client not available: {message}"
        
        try:
            # Add session context to message if provided
            if session_id and user_id:
                context_message = f"[SESSION:{session_id}|USER:{user_id}] {message}"
            else:
                context_message = message
            
            result = await self.client.invoke_agent(agent_name, context_message)
            logger.info(f"A2A call to {agent_name} successful")
            return result
        except Exception as e:
            logger.error(f"A2A call to {agent_name} failed: {e}")
            return f"Failed to communicate with {agent_name}: {str(e)}"