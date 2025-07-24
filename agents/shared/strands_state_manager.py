"""
Strands State Manager - Uses Strands built-in state management
Provides project-based context preservation and persistence
"""
from strands import Agent
from typing import Dict, Any, Optional
import json
from datetime import datetime

class StrandsStateManager:
    """Manages state using Strands built-in capabilities with project context"""
    
    def __init__(self, agent: Agent, project_id: str):
        self.agent = agent
        self.project_id = project_id
        self.context_key = f"project_{project_id}"
    
    async def save_project_context(self, context: Dict[str, Any]) -> None:
        """Save project-specific context using Strands state management"""
        try:
            # Use Strands built-in state management with session context
            if hasattr(self.agent, 'session') and self.agent.session:
                self.agent.session.context[self.context_key] = {
                    "project_id": self.project_id,
                    "context": context,
                    "updated_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"Failed to save project context: {e}")
    
    async def load_project_context(self) -> Dict[str, Any]:
        """Load project-specific context using Strands state management"""
        try:
            # Use Strands built-in state management with session context
            if hasattr(self.agent, 'session') and self.agent.session:
                state = self.agent.session.context.get(self.context_key, {})
                return state.get("context", {}) if state else {}
            return {}
        except Exception as e:
            print(f"Failed to load project context: {e}")
            return {}
    
    async def update_workflow_state(self, workflow_id: str, state: Dict[str, Any]) -> None:
        """Update workflow state within project context"""
        context = await self.load_project_context()
        
        if "workflows" not in context:
            context["workflows"] = {}
        
        context["workflows"][workflow_id] = {
            **state,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.save_project_context(context)
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow state from project context"""
        context = await self.load_project_context()
        return context.get("workflows", {}).get(workflow_id)
    
    async def save_analysis_cache(self, analysis_type: str, analysis_data: Dict[str, Any]) -> None:
        """Save analysis results in project context"""
        context = await self.load_project_context()
        
        if "analysis_cache" not in context:
            context["analysis_cache"] = {}
        
        context["analysis_cache"][analysis_type] = {
            "data": analysis_data,
            "cached_at": datetime.utcnow().isoformat()
        }
        
        await self.save_project_context(context)
    
    async def get_analysis_cache(self, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis from project context"""
        context = await self.load_project_context()
        cache = context.get("analysis_cache", {}).get(analysis_type)
        return cache.get("data") if cache else None