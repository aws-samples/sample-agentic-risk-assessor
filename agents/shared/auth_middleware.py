"""Enhanced authentication middleware supporting both user and service authentication."""

import logging
from fastapi import Request, Response
from .jwt_validator import validate_cognito_token, extract_tokens_from_headers
from .authenticated_a2a_client import set_a2a_user_context

logger = logging.getLogger(__name__)

async def enhanced_jwt_middleware(request: Request, call_next):
    """
    Enhanced JWT middleware that supports both user and service authentication.
    
    - External API calls: Require valid Cognito user tokens
    - Internal A2A calls: Use service account tokens
    - Health/discovery endpoints: Skip authentication
    """
    # Skip validation for health checks and discovery endpoints
    if request.url.path in ["/health", "/.well-known/agent.json", "/.well-known/agent-card.json"]:
        return await call_next(request)
    
    # Extract auth token and user context forwarding token
    headers_dict = dict(request.headers)
    logger.info(f"DEBUG: headers={list(headers_dict.keys())}")
    auth_token, user_context_token = extract_tokens_from_headers(headers_dict)
    logger.info(f"DEBUG: auth_token={bool(auth_token)}, user_context_token={bool(user_context_token)}")
    logger.info(f"DEBUG: authorization header={headers_dict.get('authorization', 'NOT_FOUND')}")
    
    # Handle WebSocket token from query parameters
    if 'token' in request.query_params:
        auth_token = request.query_params['token']
    
    # Check for agent authentication (Authorization header with agent scope)
    if auth_token and auth_token.startswith('Bearer '):
        logger.info(f"DEBUG: Taking Bearer token path")
        token = auth_token[7:]
        payload = validate_cognito_token(token)
        logger.info(f"DEBUG: payload={bool(payload)}, scope={payload.get('scope', 'NO_SCOPE') if payload else 'NO_PAYLOAD'}")
        if payload and 'risk-agent-api/agent.access' in payload.get('scope', ''):
            logger.info(f"DEBUG: Agent auth SUCCESS")
            request.state.auth_type = 'agent'
            request.state.agent_client_id = payload.get('client_id')
            request.state.jwt_token = token
            
            # Forward user context if provided
            if user_context_token:
                user_payload = validate_cognito_token(user_context_token)
                if user_payload:
                    request.state.user_context = user_payload
                    set_a2a_user_context(user_context_token)
            
            logger.info(f"Agent authenticated: {payload.get('client_id')} for {request.url.path}")
            return await call_next(request)
        else:
            logger.info(f"DEBUG: Agent auth FAILED - wrong scope or invalid token")
    
    # Check for user authentication (Authorization header without agent scope)
    if auth_token:
        logger.info(f"DEBUG: Taking user token path")
        token = auth_token[7:] if auth_token.startswith('Bearer ') else auth_token
        payload = validate_cognito_token(token)
        if payload and 'scope' not in payload:
            logger.info(f"DEBUG: User auth SUCCESS")
            request.state.auth_type = 'user'
            request.state.user = payload
            request.state.jwt_token = token
            set_a2a_user_context(token)
            logger.info(f"User authenticated: {payload.get('sub', 'unknown')} for {request.url.path}")
            return await call_next(request)
        else:
            logger.info(f"DEBUG: User auth FAILED - has scope or invalid token")
    else:
        logger.info(f"DEBUG: No auth_token found")
    
    # No valid authentication found
    logger.info(f"DEBUG: Reached end - returning 401")
    logger.warning(f"No authentication provided for request to {request.url.path}")
    return Response(
        content='{"error": "Authentication required"}', 
        status_code=401, 
        media_type="application/json"
    )