"""
Shared context management tools for all agents
"""
from strands.tools import tool
import logging

logger = logging.getLogger(__name__)

def create_context_management_tools(agent_instance):
    """Create context management tools for an agent"""
    
    @tool
    def clear_context() -> str:
        """Clear the agent's conversation history and context. ONLY call this when the user explicitly asks to clear or reset the conversation. Never call this automatically."""
        try:
            agent_instance.agent.messages.clear()
            logger.info("Agent context cleared successfully")
            return "OK"
        except Exception as e:
            logger.error(f"Failed to clear context: {str(e)}")
            return "ERROR"
    
    @tool
    def summarize_context() -> str:
        """Summarize the current conversation context"""
        try:
            if not hasattr(agent_instance.agent, 'messages') or not agent_instance.agent.messages:
                return "Empty"
            
            # Count messages by role
            user_messages = sum(1 for msg in agent_instance.agent.messages if msg.get('role') == 'user')
            assistant_messages = sum(1 for msg in agent_instance.agent.messages if msg.get('role') == 'assistant')
            
            return f"{len(agent_instance.agent.messages)} msgs ({user_messages}u/{assistant_messages}a)"
        except Exception as e:
            logger.error(f"Failed to summarize context: {str(e)}")
            return "ERROR"
    
    return clear_context, summarize_context