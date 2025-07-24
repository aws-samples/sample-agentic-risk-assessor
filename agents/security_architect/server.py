#!/usr/bin/env python3
"""
Security Architect Agent A2A Server
"""
import sys
sys.path.append('/app')

from agents.shared.base_server import BaseA2AServer
from agents.security_architect.agent import SecurityArchitectAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

class SecurityArchitectServer(BaseA2AServer):
    def __init__(self):
        super().__init__(
            agent_name="security-architect",
            agent_class=SecurityArchitectAgent,
            port=9004
        )
    
    def _process_agent_response(self, result: str) -> dict:
        """Process security architect specific response logic"""
        response_data = {"response": result}
        
        # Check for refresh keywords
        if "REFRESH_SECURITY_ASSESSMENT" in result:
            response_data["refresh_required"] = True
            response_data["response"] = result.replace("REFRESH_SECURITY_ASSESSMENT", "").strip()
        elif "REFRESH_CONTROL_GAP_ASSESSMENT" in result:
            response_data["refresh_required"] = True
            response_data["response"] = result.replace("REFRESH_CONTROL_GAP_ASSESSMENT", "").strip()
        
        # Check for security questionnaire structure
        if "Security Question" in result and "of" in result and "Please provide your" in result:
            lines = result.split('\n')
            question_line = None
            question_number = None
            total_questions = None
            domain = None
            category = None
            priority = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('**Security Question') and 'of' in line:
                    parts = line.replace('*', '').split()
                    if len(parts) >= 4:
                        question_number = int(parts[2])
                        total_questions = int(parts[4])
                elif line.startswith('**Security Domain:'):
                    domain = line.replace('**Security Domain:', '').replace('**', '').strip()
                elif line.startswith('**Category:'):
                    category = line.replace('**Category:', '').replace('**', '').strip()
                elif line.startswith('**Priority:'):
                    priority = line.replace('**Priority:', '').replace('**', '').strip().lower()
                elif line.startswith('**') and line.endswith('**') and '?' in line:
                    question_line = line.strip('*')
            
            if question_line:
                response_data["securityQuestion"] = {
                    "type": "security_question",
                    "question": question_line,
                    "questionNumber": question_number,
                    "totalQuestions": total_questions,
                    "domain": domain or "Security",
                    "category": category or "General",
                    "priority": priority or "medium"
                }
        
        return response_data

def create_security_architect_server():
    """Create and return security architect server"""
    server = SecurityArchitectServer()
    return server.create_server()


if __name__ == "__main__":
    server = SecurityArchitectServer()
    server.run()