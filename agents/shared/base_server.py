#!/usr/bin/env python3
"""
Base A2A Server - Shared implementation for all agents
"""
import sys
sys.path.append('/app')

from strands.multiagent.a2a import A2AServer
from strands.models import BedrockModel
import uvicorn
import asyncio
import logging
from datetime import datetime
from agents.shared.auto_refresh_credentials import create_auto_refreshing_session
from agents.shared.auth_middleware import enhanced_jwt_middleware
from fastapi import WebSocket, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import json
import os

class BaseA2AServer:
    def __init__(self, agent_name: str, agent_class, port: int, model_config: dict = None):
        self.agent_name = agent_name
        self.agent_class = agent_class
        self.port = port
        # Default model configuration from environment variables
        default_config = {
            "model_id": os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
            "temperature": float(os.getenv('BEDROCK_TEMPERATURE', '0.0')),
            "max_tokens": int(os.getenv('BEDROCK_MAX_TOKENS', '40000')),
            "timeout": int(os.getenv('BEDROCK_TIMEOUT', '300'))
        }
        
        # Merge with provided config (provided config takes precedence)
        self.model_config = {**default_config, **(model_config or {})}
        self._progress_websocket = None
        self.agent_instance = None
        self.wrapped_agent = None
        self.server = None
        
    def _build_agent_url(self) -> str:
        """Build agent URL using environment variable"""
        alb_url = os.environ.get("AGENTS_ALB_URL", "http://localhost:9000")
        # Remove trailing slash if present
        alb_url = alb_url.rstrip('/')
        return f"{alb_url}/{self.agent_name}"
    
    def _create_bedrock_model(self):
        """Create Bedrock model with conditional credentials"""
        import boto3
        import os
        
        bedrock_role_arn = os.getenv('BEDROCK_ROLE_ARN')
        
        # Determine which session to use
        if bedrock_role_arn:
            # Get current account ID
            sts_client = boto3.client('sts')
            current_account = sts_client.get_caller_identity()['Account']
            bedrock_account = bedrock_role_arn.split(':')[4]
            
            # Same account: use default session
            if current_account == bedrock_account:
                boto_session = boto3.Session()
            # Cross account: use auto-refreshing session
            else:
                boto_session = create_auto_refreshing_session(self.agent_name)
        else:
            # No role specified: use default session
            boto_session = boto3.Session()
        
        # Set HTTP read timeout for long Bedrock generations (default 60s is too short)
        from botocore.config import Config
        bedrock_config = Config(read_timeout=300, connect_timeout=10, retries={'max_attempts': 2})
        
        # Create bedrock client with extended timeout
        bedrock_client = boto_session.client('bedrock-runtime', config=bedrock_config)
        
        return BedrockModel(
            model_id=self.model_config["model_id"],
            temperature=self.model_config["temperature"],
            max_tokens=self.model_config["max_tokens"],
            boto_client=bedrock_client,
            timeout=300
        )
    
    def _create_progress_wrapper(self, agent):
        """Create A2A progress wrapper for WebSocket mirroring"""
        class A2AProgressWrapper:
            def __init__(self, agent, server_instance):
                self.agent = agent
                self.server_instance = server_instance
                self.name = getattr(agent, 'name', server_instance.agent_name)
                self.description = getattr(agent, 'description', f'{server_instance.agent_name} agent')
                # Expose underlying Strands Agent for A2A server compatibility
                self.strands_agent = getattr(agent, 'agent', agent)
                
            def __getattr__(self, name):
                # For A2A server compatibility, expose Strands Agent attributes
                if hasattr(self.agent, 'agent') and hasattr(self.agent.agent, name):
                    return getattr(self.agent.agent, name)
                return getattr(self.agent, name)
                
            async def stream_async(self, message, session_id=None, user_id=None):
                """Create fresh agent per request and stream response"""
                if self.server_instance._progress_websocket:
                    try:
                        await self.server_instance._progress_websocket.send_json({
                            "type": "agent_active",
                            "task": "Processing request"
                        })
                    except:
                        pass
                
                # Create fresh agent instance per request
                bedrock_model = self.server_instance._create_bedrock_model()
                fresh_agent = self.server_instance.agent_class(bedrock_model=bedrock_model)
                
                # Update server's agent_instance reference so progress extraction can access it
                self.server_instance.agent_instance = fresh_agent
                
                # Initialize session management for this request only
                if session_id and user_id:
                    try:
                        session_manager = fresh_agent.create_session_manager(session_id, user_id=user_id)
                        if session_manager:
                            session_manager.register_hooks(fresh_agent.agent.hooks)
                            session_manager.initialize(fresh_agent.agent)
                            
                            # Send conversation history to progress WebSocket for flow display
                            if self.server_instance._progress_websocket and hasattr(fresh_agent.agent, 'messages'):
                                try:
                                    for msg in fresh_agent.agent.messages:
                                        if msg.get('role') == 'assistant':
                                            # Send assistant messages as content for flow display
                                            for content_block in msg.get('content', []):
                                                if content_block.get('text'):
                                                    await self.server_instance._progress_websocket.send_json({
                                                        "type": "content_stream",
                                                        "content": content_block['text'],
                                                        "from_history": True
                                                    })
                                except Exception as e:
                                    print(f"Failed to send conversation history to progress WebSocket: {e}")
                    except Exception as e:
                        print(f"Session management failed: {e}, proceeding without session")
                
                # Stream from fresh agent with graceful degradation
                try:
                    async for chunk in fresh_agent.agent.stream_async(message):
                        if isinstance(chunk, dict) and "data" in chunk:
                            if self.server_instance._progress_websocket:
                                try:
                                    await self.server_instance._progress_websocket.send_json({
                                        "type": "content_stream",
                                        "content": chunk["data"]
                                    })
                                except:
                                    pass
                        elif isinstance(chunk, dict) and "current_tool_use" in chunk:
                            if self.server_instance._progress_websocket:
                                try:
                                    await self.server_instance._progress_websocket.send_json({
                                        "type": "agent_active",
                                        "task": f"Using tool: {chunk['current_tool_use']['name']}"
                                    })
                                except:
                                    pass
                        elif isinstance(chunk, str):
                            if self.server_instance._progress_websocket:
                                try:
                                    await self.server_instance._progress_websocket.send_json({
                                        "type": "content_stream",
                                        "content": chunk
                                    })
                                except:
                                    pass
                        
                        yield chunk
                except Exception as e:
                    error_msg = f"Service error: {type(e).__name__}. Response may be incomplete. Please retry."
                    print(f"[{self.server_instance.agent_name.upper()}] Bedrock stream error: {e}")
                    yield {"data": f"\n\n⚠️ {error_msg}"}
                    if self.server_instance._progress_websocket:
                        try:
                            await self.server_instance._progress_websocket.send_json({
                                "type": "error",
                                "message": error_msg
                            })
                        except:
                            pass
                
                if self.server_instance._progress_websocket:
                    try:
                        await self.server_instance._progress_websocket.send_json({
                            "type": "agent_complete"
                        })
                    except:
                        pass
                
            async def __call__(self, message, session_id=None, user_id=None):
                # Send A2A communication start event
                if self.server_instance._progress_websocket:
                    try:
                        await self.server_instance._progress_websocket.send_json({
                            "type": "a2a_communication",
                            "event": "start",
                            "to_agent": self.server_instance.agent_name,
                            "message": message[:100] + "..." if len(message) > 100 else message
                        })
                    except:
                        pass
                
                # Process with streaming and session context
                result = ""
                async for chunk in self.stream_async(message, session_id, user_id):
                    if isinstance(chunk, dict) and "data" in chunk:
                        result += chunk["data"]
                    elif isinstance(chunk, str):
                        result += chunk
                
                # Send A2A communication end event
                if self.server_instance._progress_websocket:
                    try:
                        await self.server_instance._progress_websocket.send_json({
                            "type": "a2a_communication",
                            "event": "end",
                            "to_agent": self.server_instance.agent_name,
                            "response": result[:100] + "..." if len(result) > 100 else result
                        })
                    except:
                        pass
                
                return result
        
        return A2AProgressWrapper(agent, self)
    
    def _create_agent_card_middleware(self):
        """Create middleware for agent card requests"""
        class AgentCardMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, server_instance):
                super().__init__(app)
                self.server_instance = server_instance
                
            async def dispatch(self, request, call_next):
                if request.url.path in ["/.well-known/agent-card.json"]:
                    card = self.server_instance.server.public_agent_card.model_dump()
                    card['url'] = self.server_instance._build_agent_url() + "/"
                    return Response(content=json.dumps(card), media_type="application/json")
                return await call_next(request)
        
        return AgentCardMiddleware
    
    def _add_common_endpoints(self, app):
        """Add common endpoints to A2A app"""
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "agent": self.agent_name}
        
        @app.post("/restart")
        async def restart_agent():
            # Create new agent instance
            bedrock_model = self._create_bedrock_model()
            new_agent = self.agent_class(bedrock_model=bedrock_model)
            new_wrapped_agent = self._create_progress_wrapper(new_agent)
            
            # Kill old agent
            del self.agent_instance
            del self.wrapped_agent
            
            # Atomic swap
            self.agent_instance = new_agent
            self.wrapped_agent = new_wrapped_agent
            self.server.agent = new_wrapped_agent
            
            return {"status": "restarted", "timestamp": datetime.now().isoformat()}
    
    def _add_websocket_endpoints(self, app):
        """Add WebSocket endpoints for progress and chat"""
        @app.websocket("/ws/progress")
        async def websocket_progress(websocket: WebSocket):
            token = websocket.query_params.get('token')
            if not token:
                await websocket.close(code=1008, reason="JWT token required")
                return
            
            from agents.shared.jwt_validator import validate_cognito_token
            payload = validate_cognito_token(token)
            if not payload:
                await websocket.close(code=1008, reason="Invalid JWT token")
                return
            
            self._progress_websocket = websocket
            await websocket.accept()
            print(f"[{self.agent_name.upper()}] Progress WebSocket connected")
            
            try:
                await self._progress_websocket.send_json({"type": "agent_connected"})
                while True:
                    await websocket.receive_text()
            except Exception as e:
                print(f"[{self.agent_name.upper()}] Progress WebSocket error: {e}")
            finally:
                self._progress_websocket = None
        
        @app.websocket("/ws/chat")
        async def websocket_chat(websocket: WebSocket):
            token = websocket.query_params.get('token')
            if not token:
                await websocket.close(code=1008, reason="JWT token required")
                return
            
            from agents.shared.jwt_validator import validate_cognito_token
            payload = validate_cognito_token(token)
            if not payload:
                await websocket.close(code=1008, reason="Invalid JWT token")
                return
            
            # Extract user_id and session_id
            user_id = payload['sub']
            session_id = websocket.query_params.get('session_id')
            if not session_id:
                # Generate a simple UUID-like session ID without user_id concatenation
                import uuid
                session_id = str(uuid.uuid4())
            
            await websocket.accept()
            print(f"[{self.agent_name.upper()}] Chat WebSocket connected - Session: {session_id}")
            
            try:
                while True:
                    data = await websocket.receive_json()
                    message = data.get('message', 'Hello')
                    tab_id = data.get('tab_id')
                    message_session_id = data.get('session_id')
                    
                    # Use session_id from message if provided, otherwise use WebSocket session_id
                    effective_session_id = message_session_id if message_session_id else session_id
                    
                    await websocket.send_json({"status": "processing", "agent": self.agent_name, "tab_id": tab_id})
                    
                    try:
                        # Process with streaming and session context
                        result = ""
                        async for chunk in self.wrapped_agent.stream_async(message, effective_session_id, user_id):
                            if isinstance(chunk, dict) and "data" in chunk:
                                await websocket.send_json({"type": "stream", "data": chunk["data"], "tab_id": tab_id})
                                result += chunk["data"]
                            elif isinstance(chunk, dict) and "current_tool_use" in chunk:
                                await websocket.send_json({"type": "tool", "tool": chunk["current_tool_use"]["name"], "tab_id": tab_id})
                            elif isinstance(chunk, str):
                                await websocket.send_json({"type": "stream", "data": chunk, "tab_id": tab_id})
                                result += chunk
                        
                        # Send completion with agent-specific processing
                        response_data = self._process_agent_response(result)
                        response_data.update({"type": "complete", "agent": self.agent_name, "status": "complete", "session_id": effective_session_id, "tab_id": tab_id})
                        await websocket.send_json(response_data)
                        
                    except Exception as e:
                        await websocket.send_json({"response": f"Error: {str(e)}", "status": "error", "tab_id": tab_id})
                        
            except Exception as e:
                print(f"[{self.agent_name.upper()}] Chat WebSocket error: {e}")
    
    def _process_agent_response(self, result: str) -> dict:
        """Process agent response - override in subclasses for agent-specific logic"""
        return {"response": result}
    
    def create_server(self):
        """Create and return the FastAPI server"""
        # Create Bedrock model
        bedrock_model = self._create_bedrock_model()
        
        # Create agent instance
        self.agent_instance = self.agent_class(bedrock_model=bedrock_model)
        
        # Create progress wrapper - pass BaseAgent instance, not Strands Agent
        self.wrapped_agent = self._create_progress_wrapper(self.agent_instance)
        
        # Create A2A server
        agent_url = self._build_agent_url()
        self.server = A2AServer(
            agent=self.wrapped_agent,
            http_url=agent_url,
            serve_at_root=True
        )
        
        # Get A2A app
        a2a_app = self.server.to_fastapi_app()
        
        # Add middleware
        a2a_app.add_middleware(self._create_agent_card_middleware(), server_instance=self)
        
        # Add common endpoints BEFORE JWT middleware
        self._add_common_endpoints(a2a_app)
        
        # Add WebSocket endpoints
        self._add_websocket_endpoints(a2a_app)
        
        # Create main app
        main_app = FastAPI()
        
        # Add CORS middleware with environment-based allowed origins
        allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
        main_app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add JWT middleware AFTER endpoints are defined
        main_app.middleware("http")(enhanced_jwt_middleware)
        a2a_app.middleware("http")(enhanced_jwt_middleware)
        
        # Mount A2A app
        main_app.mount(f"/{self.agent_name}", a2a_app)
        
        # Add main app middleware for agent cards
        @main_app.middleware("http")
        async def agent_card_middleware(request, call_next):
            if request.url.path in ["/.well-known/agent-card.json", f"/{self.agent_name}/.well-known/agent-card.json"]:
                card = self.server.public_agent_card.model_dump()
                card['url'] = self._build_agent_url() + "/"
                return Response(content=json.dumps(card), media_type="application/json")
            return await call_next(request)
        
        # Add main health endpoint
        @main_app.get("/health")
        async def main_health_check():
            return {"status": "healthy", "agent": self.agent_name}
        
        print(f"[{self.agent_name.upper()}] Server setup complete")
        return main_app
    
    def run(self):
        """Run the server"""
        app = self.create_server()
        # Bind to 0.0.0.0 for container networking
        host = "0.0.0.0"
        print(f"Starting {self.agent_name} Agent on {host}:{self.port}...")
        uvicorn.run(app, host=host, port=self.port, timeout_keep_alive=600, timeout_graceful_shutdown=600)