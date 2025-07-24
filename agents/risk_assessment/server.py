#!/usr/bin/env python3
"""
Risk Assessment Agent A2A Server
"""
import sys
sys.path.append('/app')

from agents.shared.base_server import BaseA2AServer
from agents.risk_assessment.agent import RiskAssessmentAgent
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

class RiskAssessmentServer(BaseA2AServer):
    def __init__(self):
        super().__init__(
            agent_name="risk-assessment",
            agent_class=RiskAssessmentAgent,
            port=9005
        )
    
    def _process_agent_response(self, result: str) -> dict:
        """Process risk assessment specific response logic"""
        response_data = {"response": result}
        
        # Check for refresh keyword
        if "REFRESH_RISK_ASSESSMENT" in result:
            response_data["refresh_required"] = True
            # Clean the keyword from response
            response_data["response"] = result.replace("REFRESH_RISK_ASSESSMENT", "").strip()
        
        return response_data

def create_risk_assessment_server():
    """Create and return risk assessment server"""
    server = RiskAssessmentServer()
    return server.create_server()


if __name__ == "__main__":
    server = RiskAssessmentServer()
    server.run()