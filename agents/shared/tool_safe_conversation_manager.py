"""
Tool-safe conversation manager that handles validation errors
"""
from strands.agent.conversation_manager import ConversationManager
from strands.types import Message
from typing import List
import logging

logger = logging.getLogger(__name__)

class ToolSafeConversationManager(ConversationManager):
    """Conversation manager that cleans up orphaned tool_use blocks"""
    
    def __init__(self):
        super().__init__()
        self.messages: List[Message] = []
    
    def add_message(self, message: Message) -> None:
        """Add message and clean up orphaned tool calls"""
        self.messages.append(message)
        self._cleanup_orphaned_tools()
    
    def get_messages(self) -> List[Message]:
        """Return cleaned messages"""
        return self.messages
    
    def _cleanup_orphaned_tools(self):
        """Remove tool_use blocks that don't have corresponding tool_result"""
        if len(self.messages) < 2:
            return
            
        # Check last two messages for orphaned tool_use
        for i in range(len(self.messages) - 1, max(0, len(self.messages) - 3), -1):
            msg = self.messages[i]
            if hasattr(msg, 'content') and isinstance(msg.content, list):
                cleaned_content = []
                for content_block in msg.content:
                    if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                        # Check if there's a corresponding tool_result
                        tool_id = getattr(content_block, 'id', None)
                        if tool_id and not self._has_tool_result(tool_id, i + 1):
                            logger.debug(f"Removing orphaned tool_use: {tool_id}")
                            continue
                    cleaned_content.append(content_block)
                
                if len(cleaned_content) != len(msg.content):
                    msg.content = cleaned_content
    
    def _has_tool_result(self, tool_id: str, start_index: int) -> bool:
        """Check if tool_result exists for given tool_id after start_index"""
        for i in range(start_index, len(self.messages)):
            msg = self.messages[i]
            if hasattr(msg, 'content') and isinstance(msg.content, list):
                for content_block in msg.content:
                    if (hasattr(content_block, 'type') and 
                        content_block.type == 'tool_result' and
                        getattr(content_block, 'tool_use_id', None) == tool_id):
                        return True
        return False