"""
Auditor Agent - Handles Quality Assurance and Validation
"""
import sys
sys.path.append('/app')

from agents.shared.base_agent import BaseAgent
from strands.tools import tool
from agents.shared import authenticated_a2a_client  # Enable OAuth authentication, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands_tools.a2a_client import A2AClientToolProvider
import boto3
import json
import os
import logging
from agents.shared.logging_config import setup_optimized_logging, setup_strands_logging

# Setup optimized logging with info level
setup_strands_logging()
logger = setup_optimized_logging(__name__, level=logging.INFO)

class AuditorAgent(BaseAgent):
    def __init__(self, bedrock_model=None):
        # Create tools
        tools = [
            self._create_validate_risk_assessment_tool(),
            self._create_validate_architecture_review_tool(),
            self._create_validate_security_assessment_tool()
        ]
        
        # Initialize BaseAgent
        super().__init__(
            agent_name="Auditor",
            bedrock_model=bedrock_model,
            system_prompt_key="system_prompts/auditor_system_prompt.xml",
            tools=tools
        )
        
        self.callback_handler = None

    
    def _refresh_bedrock_model(self):
        """Refresh bedrock model with new credentials"""
        from agents.auditor.server import refresh_bedrock_session
        from strands.models import BedrockModel
        
        new_model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            temperature=0.0,
            max_tokens=20000,
            boto_session=refresh_bedrock_session()
        )
        self.agent.model = new_model
    
    def _create_validate_risk_assessment_tool(self):
        @tool
        
        def validate_risk_assessment(assessment_content: str, project_id: str = "") -> dict:
            """Validate FSI risk assessment for completeness and consistency"""
            import time
            start_time = time.time()
            logger.info(f"TOOL CALLED: validate_risk_assessment - Project: {project_id}")
            
            try:
                from agents.auditor.tools.validation_tools import validate_risk_assessment as validate_func
                validation_results = validate_func(assessment_content)
                
                logger.info(f"Risk assessment validation completed in {time.time() - start_time:.2f}s")
                
                # Return only essential validation info to avoid large tool results
                status_emoji = "✅" if validation_results['status'] == "APPROVED" else "⚠️" if validation_results['status'] == "CONDITIONAL" else "❌"
                critical_count = len(validation_results.get('critical_issues', []))
                warning_count = len(validation_results.get('warnings', []))
                
                summary_text = f"{status_emoji} {validation_results['status']}: {validation_results['summary']}"
                if critical_count > 0:
                    summary_text += f" ({critical_count} critical issues)"
                if warning_count > 0:
                    summary_text += f" ({warning_count} warnings)"
                
                return {
                    "status": "success",
                    "content": [{"text": summary_text}]
                }
                
            except Exception as e:
                logger.error(f"Risk assessment validation failed: {str(e)}")
                return {
                    "status": "error",
                    "content": [{"text": f"Auditor Agent: ❌ REJECTED - Validation failed: {str(e)}"}]
                }
        return validate_risk_assessment
    
    def _create_validate_architecture_review_tool(self):
        @tool
        
        def validate_architecture_review(review_content: str, project_id: str = "") -> dict:
            """Validate architecture review for completeness and quality"""
            import time
            start_time = time.time()
            logger.info(f"TOOL CALLED: validate_architecture_review - Project: {project_id}")
            
            try:
                from agents.auditor.tools.validation_tools import validate_architecture_review as validate_func
                validation_results = validate_func(review_content)
                
                logger.info(f"Architecture review validation completed in {time.time() - start_time:.2f}s")
                
                # Return only essential validation info to avoid large tool results
                status_emoji = "✅" if validation_results['status'] == "APPROVED" else "⚠️" if validation_results['status'] == "CONDITIONAL" else "❌"
                critical_count = len(validation_results.get('critical_issues', []))
                warning_count = len(validation_results.get('warnings', []))
                
                summary_text = f"{status_emoji} {validation_results['status']}: {validation_results['summary']}"
                if critical_count > 0:
                    summary_text += f" ({critical_count} critical issues)"
                if warning_count > 0:
                    summary_text += f" ({warning_count} warnings)"
                
                return {
                    "status": "success",
                    "content": [{"text": summary_text}]
                }
                
            except Exception as e:
                logger.error(f"Architecture review validation failed: {str(e)}")
                return {
                    "status": "error",
                    "content": [{"text": f"Auditor Agent: ❌ REJECTED - Validation failed: {str(e)}"}]
                }
        return validate_architecture_review
    
    def _create_validate_security_assessment_tool(self):
        @tool
        
        def validate_security_assessment(assessment_content: str, project_id: str = "") -> dict:
            """Validate security assessment for completeness and compliance"""
            import time
            start_time = time.time()
            logger.info(f"TOOL CALLED: validate_security_assessment - Project: {project_id}")
            
            try:
                from agents.auditor.tools.validation_tools import validate_security_assessment as validate_func
                validation_results = validate_func(assessment_content)
                
                logger.info(f"Security assessment validation completed in {time.time() - start_time:.2f}s")
                
                # Return only essential validation info to avoid large tool results
                status_emoji = "✅" if validation_results['status'] == "APPROVED" else "⚠️" if validation_results['status'] == "CONDITIONAL" else "❌"
                critical_count = len(validation_results.get('critical_issues', []))
                warning_count = len(validation_results.get('warnings', []))
                
                summary_text = f"{status_emoji} {validation_results['status']}: {validation_results['summary']}"
                if critical_count > 0:
                    summary_text += f" ({critical_count} critical issues)"
                if warning_count > 0:
                    summary_text += f" ({warning_count} warnings)"
                
                return {
                    "status": "success",
                    "content": [{"text": summary_text}]
                }
                
            except Exception as e:
                logger.error(f"Security assessment validation failed: {str(e)}")
                return {
                    "status": "error",
                    "content": [{"text": f"Auditor Agent: ❌ REJECTED - Validation failed: {str(e)}"}]
                }
        return validate_security_assessment
    

    
    def set_progress_tracker(self, websocket):
        """Set WebSocket for progress tracking using Strands callback handler"""
        from agents.shared.progress_callback_handler import ProgressCallbackHandler
        from agents.shared.progress_hook_provider import ProgressHookProvider
        
        # Create progress callback handler
        self.callback_handler = ProgressCallbackHandler(websocket, "auditor")
        self.agent.callback_handler = self.callback_handler
        
        # Optional: Add detailed hook provider for lifecycle events
        hook_provider = ProgressHookProvider(websocket, "auditor")
        if hasattr(self.agent, '_hook_registry') and self.agent._hook_registry:
            self.agent._hook_registry.add_hook(hook_provider)
        
        # Don't send initial active signal - only activate when actually processing
        
        logger.info("Progress tracking enabled for Auditor Agent")

# Create agent instance
auditor_agent = AuditorAgent()