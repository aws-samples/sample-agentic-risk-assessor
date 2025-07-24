"""JWT token validation for Cognito User Pool tokens with service account support."""

import jwt
import requests
import boto3
import json
import os
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Cognito User Pool configuration
COGNITO_REGION = os.environ.get("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"



@lru_cache(maxsize=1)
def get_cognito_public_keys() -> Dict[str, Any]:
    """Fetch and cache Cognito public keys for JWT verification."""
    try:
        jwks_url = f"{COGNITO_ISSUER}/.well-known/jwks.json"
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Cognito public keys: {e}")
        return {}



def validate_cognito_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate JWT token issued by risk-agent Cognito User Pool.
    
    Args:
        token: JWT token string (with or without 'Bearer ' prefix)
        
    Returns:
        Decoded token payload if valid, None if invalid
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Get public keys
        jwks = get_cognito_public_keys()
        if not jwks or 'keys' not in jwks:
            logger.error("No public keys available")
            return None
        
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        # Find matching public key
        public_key = None
        for key in jwks['keys']:
            if key['kid'] == kid:
                public_key = jwt.PyJWK(key).key
                break
        
        if not public_key:
            logger.error(f"Public key not found for kid: {kid}")
            return None
        
        # Verify and decode token (cryptography now available via multi-stage build)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            issuer=COGNITO_ISSUER,
            options={
                "verify_aud": False,  # Skip audience verification for flexibility
                "verify_exp": True,   # Verify expiration
                "verify_iat": True,   # Verify issued at
                "verify_nbf": True    # Verify not before
            }
        )
        
        # Log token details for debugging
        token_use = payload.get('token_use', 'unknown')
        client_id = payload.get('client_id', 'unknown')
        sub = payload.get('sub', 'unknown')
        
        logger.info(f"Valid token - token_use: {token_use}, client_id: {client_id}, sub: {sub}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return None

def extract_tokens_from_headers(headers: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Extract both user and service JWT tokens from request headers.
    
    Returns:
        Tuple[user_token, service_token]
    """
    # Extract user token (FastAPI converts headers to lowercase)
    user_token = headers.get('x-cognito-token') or headers.get('authorization')
    
    # Extract service token
    service_token = headers.get('x-service-auth')
    
    return user_token, service_token

def extract_token_from_headers(headers: Dict[str, str]) -> Optional[str]:
    """Extract JWT token from request headers (backward compatibility)."""
    user_token, _ = extract_tokens_from_headers(headers)
    return user_token