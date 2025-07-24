#!/usr/bin/env python3
"""
Auditor Agent A2A Server
"""
import sys
sys.path.append('/app')

from agents.shared.base_server import BaseA2AServer
from agents.auditor.agent import AuditorAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

class AuditorServer(BaseA2AServer):
    def __init__(self):
        super().__init__(
            agent_name="auditor",
            agent_class=AuditorAgent,
            port=9006
        )
def create_auditor_server():
    """Create and return auditor server"""
    server = AuditorServer()
    return server.create_server()


if __name__ == "__main__":
    server = AuditorServer()
    server.run()