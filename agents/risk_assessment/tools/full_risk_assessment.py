"""
Full Risk Assessment Tool for Risk Assessment Agent
Performs comprehensive FSI risk assessment using templates and A2A communication
"""

import json
import logging
import os
import boto3
from typing import Dict, Any, List
from strands_tools.a2a_client import A2AClient

logger = logging.getLogger(__name__)

class FullRiskAssessmentTool:
    """Tool to perform comprehensive FSI risk assessment"""
    
    def __init__(self, a2a_client: A2AClient):
        self.a2a_client = a2a_client
        self.s3_client = boto3.client('s3')
        self.bucket = os.getenv('APP_DATA_BUCKET')
        
    async def perform_full_risk_assessment(self, project_id: str, framework: str = "FSI") -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment following FSI framework template
        
        Args:
            project_id: Project identifier
            framework: Risk framework to use (default: FSI)
            
        Returns:
            Complete risk assessment following FSI template
        """
        try:
            logger.info(f"Starting full risk assessment for project {project_id}")
            
            # Step 1: Get business context from architect agent
            business_context = await self._get_business_context(project_id)
            
            # Step 2: Get technical issues from architect agent
            technical_issues = await self._get_technical_issues(project_id)
            
            # Step 3: Get security issues from security architect agent
            security_issues = await self._get_security_issues(project_id)
            
            # Step 4: Perform FSI risk assessment
            risk_assessment = await self._perform_fsi_assessment(
                project_id, business_context, technical_issues, security_issues
            )
            
            return {
                "status": "success",
                "content": [
                    {"text": f"Full risk assessment completed for project {project_id}"},
                    {"json": {
                        "project_id": project_id,
                        "framework": framework,
                        "assessment": risk_assessment
                    }}
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in full risk assessment: {str(e)}")
            return {
                "status": "error",
                "content": [{"text": f"Error in full risk assessment: {str(e)}"}]
            }
    
    async def _get_business_context(self, project_id: str) -> Dict[str, Any]:
        """Get business context from architect agent"""
        try:
            prompts = self._load_prompts()
            prompt = prompts["business_context_prompt"].format(project_id=project_id)
            response = await self.a2a_client.invoke_agent("architect", prompt)
            return {"business_context": response.get("content", "")}
        except Exception as e:
            logger.error(f"Error getting business context: {str(e)}")
            return {"business_context": "Unable to retrieve business context"}
    
    async def _get_technical_issues(self, project_id: str) -> Dict[str, Any]:
        """Get technical issues from architect agent"""
        try:
            prompts = self._load_prompts()
            prompt = prompts["technical_issues_prompt"].format(project_id=project_id)
            response = await self.a2a_client.invoke_agent("architect", prompt)
            return {"technical_issues": response.get("content", "")}
        except Exception as e:
            logger.error(f"Error getting technical issues: {str(e)}")
            return {"technical_issues": "Unable to retrieve technical issues"}
    
    async def _get_security_issues(self, project_id: str) -> Dict[str, Any]:
        """Get security issues from security architect agent"""
        try:
            prompts = self._load_prompts()
            prompt = prompts["security_issues_prompt"].format(project_id=project_id)
            response = await self.a2a_client.invoke_agent("security_architect", prompt)
            return {"security_issues": response.get("content", "")}
        except Exception as e:
            logger.error(f"Error getting security issues: {str(e)}")
            return {"security_issues": "Unable to retrieve security issues"}
    
    def _load_template(self) -> Dict[str, Any]:
        """Load FSI assessment template from S3"""
        response = self.s3_client.get_object(
            Bucket=self.bucket,
            Key='risk_assessment/templates/fsi_assessment_template.json'
        )
        return json.loads(response['Body'].read().decode('utf-8'))
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load agent prompts from S3"""
        response = self.s3_client.get_object(
            Bucket=self.bucket,
            Key='risk_assessment/templates/agent_prompts.json'
        )
        return json.loads(response['Body'].read().decode('utf-8'))
    
    async def _perform_fsi_assessment(self, project_id: str, business_context: Dict, 
                                    technical_issues: Dict, security_issues: Dict) -> Dict[str, Any]:
        """Perform FSI risk assessment using gathered information"""
        
        assessment_template = self._load_template()
        
        assessment_template["business_context"]["business_objectives"] = business_context.get("business_context", "")
        assessment_template["executive_summary"]["project_overview"] = f"Risk assessment for project {project_id}"
        
        if technical_issues.get("technical_issues"):
            assessment_template["risk_categories"]["technology_cyber_risk"]["scenarios"].append({
                "description": "Technical Architecture Risks",
                "details": technical_issues["technical_issues"],
                "likelihood": "Possible",
                "impact": "Moderate",
                "risk_level": "Medium"
            })
        
        if security_issues.get("security_issues"):
            assessment_template["risk_categories"]["technology_cyber_risk"]["scenarios"].append({
                "description": "Security and Compliance Risks", 
                "details": security_issues["security_issues"],
                "likelihood": "Likely",
                "impact": "Major",
                "risk_level": "High"
            })
        
        return assessment_template

def create_tool(a2a_client: A2AClient):
    """Factory function to create the tool"""
    tool = FullRiskAssessmentTool(a2a_client)
    return tool.perform_full_risk_assessment