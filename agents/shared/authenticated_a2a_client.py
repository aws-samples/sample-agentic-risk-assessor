"""OAuth authenticated A2A Client."""

import logging
import os
from typing import Dict, Optional
import httpx
from .oauth_client_auth import get_agent_token

logger = logging.getLogger(__name__)

# Get agent name from environment
AGENT_NAME = os.getenv('AGENT_NAME', 'unknown')

def get_auth_headers() -> Dict[str, str]:
    """Get OAuth authentication headers for A2A requests."""
    try:
        token = get_agent_token(AGENT_NAME)
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
            # Forward user context if available
            user_context = get_a2a_user_context()
            if user_context:
                headers['X-Service-Auth'] = user_context
            
            return headers
        else:
            logger.error(f"Failed to get OAuth token for agent {AGENT_NAME}")
            return {}
    except Exception as e:
        logger.error(f"Failed to get OAuth token for agent {AGENT_NAME}: {e}")
        return {}

# Store original request method for patching
_original_httpx_request = httpx.AsyncClient.request
_patch_applied = False

def patch_a2a_client():
    """Patch A2A client to include OAuth authentication."""
    global _patch_applied
    if _patch_applied:
        return
    
    async def authenticated_request(self, method, url, **kwargs):
        # Get OAuth auth headers
        auth_headers = get_auth_headers()
        
        if auth_headers:
            headers = kwargs.get('headers', {})
            if isinstance(headers, dict):
                headers = headers.copy()
            else:
                headers = dict(headers) if headers else {}
            
            # Add OAuth authentication headers
            headers.update(auth_headers)
            kwargs['headers'] = headers
            
            logger.info(f"Adding OAuth auth to A2A request: {method} {url}")
        else:
            logger.warning(f"No OAuth auth headers available for A2A request: {method} {url}")
        
        return await _original_httpx_request(self, method, url, **kwargs)
    
    httpx.AsyncClient.request = authenticated_request
    _patch_applied = True
    logger.info("A2A client patched for OAuth authentication")

# Global user context for A2A forwarding
_user_context = None

def set_a2a_user_context(user_token: str):
    """Set user context for A2A forwarding."""
    global _user_context
    _user_context = user_token
    logger.info("User context set for A2A forwarding")

def get_a2a_user_context() -> Optional[str]:
    """Get current user context for A2A forwarding."""
    return _user_context

# Apply the patch
patch_a2a_client()