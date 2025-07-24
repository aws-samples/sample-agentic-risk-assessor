"""
Get Agent Capabilities Lambda - Fetches tool capabilities from Strands agents
"""
import json
import boto3
import os
import logging
from typing import Dict, List, Any
import requests
from urllib.parse import urljoin

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_agent_urls() -> Dict[str, str]:
    """Get agent URLs from environment or configuration"""
    base_url = os.getenv('AGENT_BASE_URL', '')
    
    return {
        'architect': f"{base_url}/architect",
        'security-architect': f"{base_url}/security-architect", 
        'risk-assessment': f"{base_url}/risk-assessment",
        'orchestrator': f"{base_url}/orchestrator",
        'risk-framework': f"{base_url}/risk-framework"
    }

def fetch_agent_capabilities(agent_url: str) -> Dict[str, Any]:
    """Fetch capabilities from a Strands agent via its agent card endpoint"""
    try:
        # Strands agents expose their capabilities at /.well-known/agent-card.json
        card_url = f"{agent_url}/.well-known/agent-card.json"
        response = requests.get(card_url, timeout=10)
        response.raise_for_status()
        
        agent_card = response.json()
        
        # Extract skills from agent card (Strands agents use 'skills' not 'tools')
        skills = agent_card.get('skills', [])
        capabilities = []
        
        for skill in skills:
            # Extract skill information from Strands skill definition
            skill_name = skill.get('name', 'Unknown Skill')
            skill_description = skill.get('description', '')
            
            # Generate friendly name from skill name
            friendly_name = skill_name.replace('_', ' ').title()
            
            # Generate user message from description or skill name
            if skill_description:
                # Use first sentence of description as message
                message = skill_description.split('.')[0].lower()
                if not message.startswith(('get', 'analyze', 'perform', 'save', 'update', 'process')):
                    message = f"use {skill_name.replace('_', ' ')}"
            else:
                message = f"use {skill_name.replace('_', ' ')}"
            
            capabilities.append({
                'name': friendly_name,
                'message': message,
                'skill_name': skill_name,
                'description': skill_description
            })
        
        return {
            'agent': agent_card.get('name', 'Unknown Agent'),
            'capabilities': capabilities,
            'status': 'success'
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch capabilities from {agent_url}/.well-known/agent-card.json: {str(e)}")
        return {
            'agent': 'Unknown',
            'capabilities': [],
            'status': 'error',
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"Error processing agent capabilities from {agent_url}/.well-known/agent-card.json: {str(e)}")
        return {
            'agent': 'Unknown', 
            'capabilities': [],
            'status': 'error',
            'error': str(e)
        }

def lambda_handler(event, context):
    """
    Lambda handler to fetch agent capabilities dynamically
    """
    try:
        logger.info(f"Fetching agent capabilities - Event: {json.dumps(event)}")
        
        # Get agent URLs
        agent_urls = get_agent_urls()
        
        # Fetch capabilities from all agents
        all_capabilities = {}
        
        for agent_name, agent_url in agent_urls.items():
            logger.info(f"Fetching capabilities for {agent_name} from {agent_url}")
            capabilities = fetch_agent_capabilities(agent_url)
            all_capabilities[agent_name] = capabilities['capabilities']
        
        response_body = {
            'capabilities': all_capabilities,
            'status': 'success'
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Error in get_agent_capabilities: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Failed to fetch agent capabilities',
                'details': str(e)
            })
        }