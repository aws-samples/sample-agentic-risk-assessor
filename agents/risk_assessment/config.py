"""
Configuration for Risk Assessment Agent
"""
import os

class RiskAssessmentConfig:
    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.projects_table = os.getenv('PROJECTS_TABLE', 'risk-agent-projects')
        self.node_controls_table = os.getenv('NODE_CONTROLS_TABLE', 'risk-agent-node-controls')
        self.bedrock_results_table = os.getenv('BEDROCK_RESULTS_TABLE', 'risk-agent-bedrock-results')
        
    def to_dict(self):
        return {
            'aws_region': self.aws_region,
            'projects_table': self.projects_table,
            'node_controls_table': self.node_controls_table,
            'bedrock_results_table': self.bedrock_results_table
        }