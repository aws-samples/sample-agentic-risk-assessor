"""
Configuration for Security Architect Agent
"""
import os

class SecurityArchitectConfig:
    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.projects_table = os.getenv('PROJECTS_TABLE', 'risk-agent-projects')
        self.clarifications_table = os.getenv('CLARIFICATIONS_TABLE', 'risk-agent-clarifications')
        self.diagram_analysis_table = os.getenv('DIAGRAM_ANALYSIS_TABLE', 'risk-agent-diagram-analysis')
        self.node_controls_table = os.getenv('NODE_CONTROLS_TABLE', 'risk-agent-node-controls')
        
    def to_dict(self):
        return {
            'aws_region': self.aws_region,
            'projects_table': self.projects_table,
            'clarifications_table': self.clarifications_table,
            'diagram_analysis_table': self.diagram_analysis_table,
            'node_controls_table': self.node_controls_table
        }