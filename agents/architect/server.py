#!/usr/bin/env python3
"""
Architect Agent A2A Server
"""
import sys
sys.path.append('/app')

from agents.shared.base_server import BaseA2AServer
from agents.architect.agent import ArchitectAgent
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

class ArchitectServer(BaseA2AServer):
    def __init__(self):
        super().__init__(
            agent_name="architect",
            agent_class=ArchitectAgent,
            port=9002
        )
    
    def _process_agent_response(self, result: str) -> dict:
        """Process architect-specific response logic"""
        response_data = {"response": result}
        
        # Check for refresh diagram keyword
        if "REFRESH_DIAGRAM" in result:
            print(f"[ARCHITECT] 🔄 Detected REFRESH_DIAGRAM in response")
            response_data["refresh_required"] = True
            # Clean the keyword from response
            response_data["response"] = result.replace("REFRESH_DIAGRAM", "").replace("  ", " ").strip()
        
        # Check for multiple choice structure
        if "Question" in result and "of" in result and "Please choose from:" in result:
            lines = result.split('\n')
            question_line = None
            options = []
            question_number = None
            total_questions = None
            category = None
            priority = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('**Question') and 'of' in line:
                    parts = line.replace('*', '').split()
                    if len(parts) >= 4:
                        question_number = int(parts[1])
                        total_questions = int(parts[3])
                elif line.startswith('**Category:'):
                    category = line.replace('**Category:', '').replace('**', '').strip()
                elif line.startswith('**Priority:'):
                    priority = line.replace('**Priority:', '').replace('**', '').strip().lower()
                elif line.startswith('**') and line.endswith('**') and '?' in line:
                    question_line = line.strip('*')
                elif line and line[0].isdigit() and '. ' in line:
                    option_text = line.split('. ', 1)[1]
                    options.append({"id": str(len(options) + 1), "text": option_text})
            
            if question_line and options:
                response_data["multipleChoice"] = {
                    "type": "multiple_choice",
                    "question": question_line,
                    "options": options,
                    "questionNumber": question_number,
                    "totalQuestions": total_questions,
                    "category": category or "Architecture",
                    "priority": priority or "medium"
                }
        
        return response_data

def create_architect_server():
    """Create and return architect server"""
    server = ArchitectServer()
    return server.create_server()


if __name__ == "__main__":
    server = ArchitectServer()
    server.run()