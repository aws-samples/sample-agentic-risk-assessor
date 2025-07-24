import boto3
import os

class TriageTool:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('APP_DATA_BUCKET')
        self.prompt_key = 'system_prompts/security_architect/triage_security_assessment.md'

    def get_triage_prompt(self) -> str:
        """Read triage prompt from S3"""
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=self.prompt_key
        )
        return response['Body'].read().decode('utf-8')