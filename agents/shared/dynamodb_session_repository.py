import boto3
import json
import os
from decimal import Decimal
from datetime import datetime
from typing import Any, Optional
from boto3.dynamodb.conditions import Key
from strands.session import SessionRepository
from strands.types.session import Session, SessionAgent, SessionMessage


def _sanitize_decimals(obj):
    """Convert Decimal values to int/float for DynamoDB document compatibility."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    elif isinstance(obj, dict):
        return {k: _sanitize_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_decimals(i) for i in obj]
    return obj


def _truncate_large_content(obj, max_str_len=50000):
    """Truncate large string values to keep DynamoDB items under 400KB."""
    if isinstance(obj, str) and len(obj) > max_str_len:
        return obj[:max_str_len] + "\n\n[... truncated for storage]"
    elif isinstance(obj, dict):
        return {k: _truncate_large_content(v, max_str_len) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_truncate_large_content(i, max_str_len) for i in obj]
    return obj


class DynamoDBSessionRepository(SessionRepository):
    """DynamoDB implementation of Strands SessionRepository interface."""
    
    def __init__(self):
        table_name = os.getenv('SESSIONS_TABLE')
        if not table_name:
            raise ValueError("SESSIONS_TABLE environment variable not set")
        self.table = boto3.resource('dynamodb').Table(table_name)
        
        # Agent name mapping for session compatibility
        self.agent_name_mapping = {
            'SecurityArchitect': 'security-architect',
            'RiskAssessment': 'risk-assessment', 
            'Architect': 'architect',
            'Auditor': 'auditor',
            # Server name to agent name mapping (keep frontend format)
            'security_architect': 'security-architect',
            'risk_assessment': 'risk-assessment',
            'security-architect': 'security-architect',
            'risk-assessment': 'risk-assessment',
            'auditor': 'auditor'
        }
        
        # Reverse mapping for lookups
        self.reverse_agent_mapping = {
            'security-architect': 'SecurityArchitect',
            'risk-assessment': 'RiskAssessment',
            'architect': 'Architect',
            'auditor': 'Auditor'
        }
    
    def _normalize_agent_id(self, agent_id: str) -> str:
        """Normalize agent ID for consistent storage and retrieval"""
        # Convert to frontend format (lowercase with hyphens) for storage
        return self.agent_name_mapping.get(agent_id, agent_id.lower().replace(' ', '-').replace('_', '-'))

    def _truncate_for_dynamo(self, data: dict, max_bytes: int = 350000) -> dict:
        """Truncate message data to fit DynamoDB 400KB item limit."""
        import json
        serialized = json.dumps(data, default=str)
        if len(serialized.encode('utf-8')) <= max_bytes:
            return data
        for key in ['content', 'text', 'body', 'response']:
            if key in data and isinstance(data[key], str) and len(data[key]) > 10000:
                data[key] = data[key][:50000] + '\n\n[... truncated for storage ...]'
        serialized = json.dumps(data, default=str)
        if len(serialized.encode('utf-8')) > max_bytes:
            for key in data:
                if isinstance(data[key], str) and len(data[key]) > 5000:
                    data[key] = data[key][:5000] + '\n[truncated]'
                elif isinstance(data[key], list) and len(str(data[key])) > 50000:
                    data[key] = data[key][:10]
        return data
    
    def _denormalize_agent_id(self, normalized_id: str) -> str:
        """Convert normalized agent ID back to original format"""
        return self.reverse_agent_mapping.get(normalized_id, normalized_id)
    
    def create_session(self, session: Session, **kwargs: Any) -> Session:
        """Create a new Session."""
        try:
            agent_id = kwargs.get('agent_id', 'unknown')
            stored_user_id = getattr(self, '_current_user_id', None)
            user_id = stored_user_id or kwargs.get('user_id', 'unknown')
            timestamp = datetime.now().isoformat()
            
            print(f"DEBUG: Creating session - session_id: {session.session_id}, agent_id: {agent_id}, user_id: {user_id}, stored_user_id: {stored_user_id}, kwargs: {list(kwargs.keys())}")
            
            self.table.put_item(
                Item={
                    'session_id': session.session_id,
                    'sort_key': f'SESSION#{timestamp}',
                    'record_type': 'session',
                    'timestamp': timestamp,
                    'user_id': user_id,
                    'agent_id': agent_id,
                    'IsActive': True,
                    'data': _sanitize_decimals(session.to_dict())
                }
            )
            print(f"DEBUG: Session created successfully")
            return session
        except Exception as e:
            print(f"Error creating session: {e}")
            raise
    
    def read_session(self, session_id: str, **kwargs: Any) -> Optional[Session]:
        """Read a Session."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key('session_id').eq(session_id) & Key('sort_key').begins_with('SESSION#'),
                Limit=1
            )
            items = response.get('Items', [])
            if items:
                return Session.from_dict(_sanitize_decimals(items[0]['data']))
            return None
        except Exception as e:
            print(f"Error reading session: {e}")
            return None
    
    def create_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        """Create a new Agent in a Session."""
        try:
            normalized_agent_id = self._normalize_agent_id(session_agent.agent_id)
            timestamp = datetime.now().isoformat()
            stored_user_id = getattr(self, '_current_user_id', None)
            user_id = stored_user_id or kwargs.get('user_id', 'unknown')
            print(f"DEBUG: Creating agent - original: {session_agent.agent_id}, normalized: {normalized_agent_id}, stored_user_id: {stored_user_id}, user_id: {user_id}, kwargs: {list(kwargs.keys())}")
            
            self.table.put_item(
                Item={
                    'session_id': session_id,
                    'sort_key': f'AGENT#{normalized_agent_id}#{timestamp}',
                    'record_type': 'agent',
                    'timestamp': timestamp,
                    'user_id': user_id,
                    'agent_id': normalized_agent_id,
                    'original_agent_id': session_agent.agent_id,
                    'IsActive': True,
                    'data': _sanitize_decimals(session_agent.to_dict())
                }
            )
        except Exception as e:
            print(f"Error creating agent: {e}")
            raise
    
    def read_agent(self, session_id: str, agent_id: str, **kwargs: Any) -> Optional[SessionAgent]:
        """Read an Agent."""
        try:
            normalized_agent_id = self._normalize_agent_id(agent_id)
            stored_user_id = getattr(self, '_current_user_id', None)
            print(f"DEBUG: Reading agent - original: {agent_id}, normalized: {normalized_agent_id}, stored_user_id: {stored_user_id}")
            
            response = self.table.query(
                KeyConditionExpression=Key('session_id').eq(session_id) & Key('sort_key').begins_with(f'AGENT#{normalized_agent_id}#'),
                ScanIndexForward=False,  # Get latest first
                Limit=1
            )
            items = response.get('Items', [])
            if items:
                return SessionAgent.from_dict(_sanitize_decimals(items[0]['data']))
            return None
        except Exception as e:
            print(f"Error reading agent: {e}")
            return None
    
    def update_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        """Update an Agent."""
        try:
            normalized_agent_id = self._normalize_agent_id(session_agent.agent_id)
            timestamp = datetime.now().isoformat()
            stored_user_id = getattr(self, '_current_user_id', None)
            user_id = stored_user_id or kwargs.get('user_id', 'unknown')
            
            self.table.put_item(
                Item={
                    'session_id': session_id,
                    'sort_key': f'AGENT#{normalized_agent_id}#{timestamp}',
                    'record_type': 'agent',
                    'timestamp': timestamp,
                    'user_id': user_id,
                    'agent_id': normalized_agent_id,
                    'original_agent_id': session_agent.agent_id,
                    'IsActive': True,
                    'data': _sanitize_decimals(session_agent.to_dict())
                }
            )
        except Exception as e:
            print(f"Error updating agent: {e}")
            raise
    
    def set_current_user_id(self, user_id: str):
        """Set the current user ID for this session repository instance"""
        self._current_user_id = user_id
        print(f"DEBUG: Set current user_id to: {user_id}")
    
    def create_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        """Create a new Message for the Agent."""
        try:
            normalized_agent_id = self._normalize_agent_id(agent_id)
            message_id = getattr(session_message, 'message_id', 0)
            if message_id is None:
                message_id = 0
            
            stored_user_id = getattr(self, '_current_user_id', None)
            user_id = stored_user_id or kwargs.get('user_id', 'unknown')
            timestamp = datetime.now().isoformat()
            
            print(f"DEBUG: Creating message - session_id: {session_id}, original_agent_id: {agent_id}, normalized_agent_id: {normalized_agent_id}, user_id: {user_id}, stored_user_id: {stored_user_id}, message_id: {message_id}, kwargs: {list(kwargs.keys())}")
            
            message_data = self._truncate_for_dynamo(session_message.to_dict())
            
            # Truncate large message data to stay within DynamoDB 400KB limit
            sanitized_data = _sanitize_decimals(message_data)
            sanitized_data = _truncate_large_content(sanitized_data)
            
            self.table.put_item(
                Item={
                    'session_id': session_id,
                    'sort_key': f'MESSAGE#{normalized_agent_id}#{int(message_id):06d}#{timestamp}',
                    'record_type': 'message',
                    'timestamp': timestamp,
                    'user_id': user_id,
                    'agent_id': normalized_agent_id,
                    'original_agent_id': agent_id,
                    'message_id': int(message_id),
                    'IsActive': True,
                    'data': sanitized_data
                }
            )
            print(f"DEBUG: Message created successfully")
        except Exception as e:
            print(f"Error creating message: {e}")
            raise
    
    def read_message(self, session_id: str, agent_id: str, message_id: int, **kwargs: Any) -> Optional[SessionMessage]:
        """Read a Message."""
        try:
            normalized_agent_id = self._normalize_agent_id(agent_id)
            response = self.table.query(
                KeyConditionExpression=Key('session_id').eq(session_id) & Key('sort_key').begins_with(f'MESSAGE#{normalized_agent_id}#{int(message_id):06d}#'),
                Limit=1
            )
            items = response.get('Items', [])
            if items:
                return SessionMessage.from_dict(_sanitize_decimals(items[0]['data']))
            return None
        except Exception as e:
            print(f"Error reading message: {e}")
            return None
    
    def update_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        """Update a Message."""
        try:
            normalized_agent_id = self._normalize_agent_id(agent_id)
            message_id = getattr(session_message, 'message_id', 0)
            if message_id is None:
                message_id = 0
            
            stored_user_id = getattr(self, '_current_user_id', None)
            user_id = stored_user_id or kwargs.get('user_id', 'unknown')
            timestamp = datetime.now().isoformat()
            
            self.table.put_item(
                Item={
                    'session_id': session_id,
                    'sort_key': f'MESSAGE#{normalized_agent_id}#{int(message_id):06d}#{timestamp}',
                    'record_type': 'message',
                    'timestamp': timestamp,
                    'user_id': user_id,
                    'agent_id': normalized_agent_id,
                    'original_agent_id': agent_id,
                    'message_id': int(message_id),
                    'IsActive': True,
                    'data': _sanitize_decimals(session_message.to_dict())
                }
            )
        except Exception as e:
            print(f"Error updating message: {e}")
            raise
    
    def list_messages(
        self, session_id: str, agent_id: str, limit: Optional[int] = None, offset: int = 0, **kwargs: Any
    ) -> list[SessionMessage]:
        """List Messages from an Agent with pagination."""
        import time
        start_time = time.time()
        try:
            normalized_agent_id = self._normalize_agent_id(agent_id)
            query_params = {
                'KeyConditionExpression': Key('session_id').eq(session_id) & Key('sort_key').begins_with(f'MESSAGE#{normalized_agent_id}#'),
                'ScanIndexForward': True  # Sort by sort_key ascending (message_id order)
            }
            # Add DynamoDB Limit if specified to avoid scanning all items
            if limit:
                query_params['Limit'] = limit + offset  # Account for offset
            
            print(f"[DYNAMO_DEBUG] Querying with limit={limit}, offset={offset}, actual_limit={query_params.get('Limit')}")
            query_start = time.time()
            response = self.table.query(**query_params)
            query_time = time.time() - query_start
            print(f"[DYNAMO_DEBUG] Query returned {len(response['Items'])} items in {query_time:.3f}s")
            
            parse_start = time.time()
            messages = []
            for item in response['Items']:
                if item['message_id'] >= offset:
                    messages.append(SessionMessage.from_dict(_sanitize_decimals(item['data'])))
                    if limit and len(messages) >= limit:
                        break
            parse_time = time.time() - parse_start
            
            total_time = time.time() - start_time
            print(f"[DYNAMO_DEBUG] Parsed {len(messages)} messages in {parse_time:.3f}s, total: {total_time:.3f}s")
            return messages
        except Exception as e:
            print(f"Error listing messages: {e}")
            return []