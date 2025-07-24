#!/usr/bin/env python3
"""
A2A Agent Discovery Utilities
"""
import os
import yaml
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def _load_discovery_config() -> Dict:
    """Load agents configuration from config/a2a_discovery.yaml"""
    config_paths = [
        '/app/config/a2a_discovery.yaml',
        os.path.join(os.path.dirname(__file__), '../../config/a2a_discovery.yaml'),
        os.path.join(os.getcwd(), 'config/a2a_discovery.yaml')
    ]
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
    
    raise FileNotFoundError("a2a_discovery.yaml configuration file not found")

def _get_agent_urls_from_config() -> List[str]:
    """Get agent URLs from discovery configuration"""
    config = _load_discovery_config()
    agents = config.get('agents', {})
    alb_url = os.environ.get('AGENTS_ALB_URL', 'http://localhost:9000')
    
    urls = []
    for agent_key, agent_config in agents.items():
        if agent_key == 'risk_framework':
            continue  # Skip risk_framework as it's not deployed as separate service
        url_template = agent_config.get('url', f'{alb_url}/{agent_key}')
        # Replace environment variable placeholder
        url = url_template.replace('${AGENTS_ALB_URL}', alb_url)
        urls.append(url)
    
    return urls

def get_agent_urls(agent_name: str = None) -> List[str]:
    """Get list of known agent URLs for discovery"""
    alb_url = os.environ.get('AGENTS_ALB_URL')
    if not alb_url:
        logger.error(f"AGENTS_ALB_URL environment variable not set. Available env vars: {list(os.environ.keys())}")
        raise ValueError("AGENTS_ALB_URL environment variable not set")
    
    logger.info(f"Using AGENTS_ALB_URL: {alb_url}")
    
    # Get agent URLs from discovery configuration
    urls = _get_agent_urls_from_config()
    
    logger.info(f"Generated agent URLs from config: {urls}")
    return urls

def get_agent_info(agent_name: str, requesting_agent: str = None) -> Optional[Dict]:
    """Get specific agent information"""
    alb_url = os.environ.get('AGENTS_ALB_URL')
    if not alb_url:
        return None
    
    config = _load_discovery_config()
    agents = config.get('agents', {})
    agent_config = agents.get(agent_name)
    
    if agent_config:
        url_template = agent_config.get('url', f'{alb_url}/{agent_name}')
        url = url_template.replace('${AGENTS_ALB_URL}', alb_url)
        return {'url': url, 'description': agent_config.get('description', '')}
    
    return None