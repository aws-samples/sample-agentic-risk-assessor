"""
Strands-native Base Agent with proper session management and telemetry
"""
import sys
sys.path.append('/app')

from strands import Agent
from strands.session import RepositorySessionManager
from strands.types.session import Session, SessionAgent, SessionMessage
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands_tools.a2a_client import A2AClientToolProvider
from agents.shared import authenticated_a2a_client  # Enable OAuth authentication
import boto3
import json
import os
import logging
from typing import Optional, Any
from agents.shared.logging_config import setup_optimized_logging, setup_strands_logging
from agents.shared.dynamodb_session_repository import DynamoDBSessionRepository

# Strands telemetry for proper observability
try:
    from strands.telemetry import StrandsTelemetry
    telemetry_available = True
except ImportError:
    telemetry_available = False

# Langfuse configuration check
try:
    from agents.shared.langfuse_client import is_enabled
    langfuse_enabled = is_enabled()
except ImportError:
    langfuse_enabled = False
# Setup optimized logging
setup_strands_logging()
logger = setup_optimized_logging(__name__, level=logging.INFO)

class BaseAgent:
    def __init__(self, agent_name: str, bedrock_model=None, system_prompt_key: str = None, tools: list = None):
        import time
        base_init_start = time.time()
        print(f"[BASE_DEBUG] BaseAgent.__init__ started")
        
        self.agent_name = agent_name
        self.lambda_client = boto3.client('lambda')
        
        # Setup Strands telemetry if available and Langfuse is enabled
        telemetry_start = time.time()
        if telemetry_available and langfuse_enabled:
            try:
                # Set required OTEL environment variables for Langfuse integration
                import base64
                langfuse_public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
                langfuse_secret_key = os.getenv('LANGFUSE_SECRET_KEY')
                langfuse_host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
                
                if langfuse_public_key and langfuse_secret_key:
                    # Build Basic Auth header
                    langfuse_auth = base64.b64encode(
                        f"{langfuse_public_key}:{langfuse_secret_key}".encode()
                    ).decode()
                    
                    # Set OTEL environment variables
                    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{langfuse_host}/api/public/otel/v1/traces"
                    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"
                    
                    # Setup telemetry
                    strands_telemetry = StrandsTelemetry()
                    strands_telemetry.setup_otlp_exporter()
                    logger.info(f"Strands telemetry configured for {agent_name} with Langfuse endpoint")
                else:
                    logger.warning("Langfuse credentials not found, telemetry disabled")
            except Exception as e:
                logger.warning(f"Failed to setup telemetry: {e}")
        telemetry_time = time.time() - telemetry_start
        print(f"[BASE_DEBUG] Telemetry setup: {telemetry_time:.3f}s")
        
        # Load system prompt from S3 if provided
        prompt_start = time.time()
        if system_prompt_key:
            system_prompt = self._load_system_prompt(system_prompt_key)
        else:
            system_prompt = f"You are the {agent_name} agent."
        prompt_time = time.time() - prompt_start
        print(f"[BASE_DEBUG] System prompt loaded: {prompt_time:.3f}s")
        
        # Add context management tools
        context_tools_start = time.time()
        from agents.shared.context_tools import create_context_management_tools
        clear_context_tool, summarize_context_tool = create_context_management_tools(self)
        context_tools_time = time.time() - context_tools_start
        print(f"[BASE_DEBUG] Context management tools created: {context_tools_time:.3f}s")
        
        # Setup A2A client for agent communication
        a2a_start = time.time()
        print(f"[BASE_DEBUG] Starting A2A setup...")
        a2a_tools = []
        try:
            import_start = time.time()
            from agents.shared.a2a_discovery import get_agent_urls
            import_time = time.time() - import_start
            print(f"[BASE_DEBUG] A2A imports: {import_time:.3f}s")
            
            discovery_start = time.time()
            agent_urls = get_agent_urls(agent_name=agent_name.lower())
            discovery_time = time.time() - discovery_start
            print(f"[BASE_DEBUG] A2A discovery: {discovery_time:.3f}s")
            logger.info(f"Using A2A agent URLs: {agent_urls}")
            
            # Initialize A2A provider with connection fix
            provider_start = time.time()
            logger.info("Initializing A2A client provider...")
            a2a_provider = A2AClientToolProvider(known_agent_urls=agent_urls)
            provider_time = time.time() - provider_start
            print(f"[BASE_DEBUG] A2A provider init: {provider_time:.3f}s")
            
            # Patch the HTTP client creation to disable connection reuse
            patch_start = time.time()
            import httpx
            original_ensure_httpx_client = a2a_provider._ensure_httpx_client
            
            async def patched_ensure_httpx_client():
                if a2a_provider._httpx_client is None:
                    a2a_provider._httpx_client = httpx.AsyncClient(
                        timeout=a2a_provider.timeout,
                        limits=httpx.Limits(max_keepalive_connections=0)
                    )
                return a2a_provider._httpx_client
            
            a2a_provider._ensure_httpx_client = patched_ensure_httpx_client
            patch_time = time.time() - patch_start
            print(f"[BASE_DEBUG] HTTP client patching: {patch_time:.3f}s")
            
            tools_start = time.time()
            a2a_tools = a2a_provider.tools
            tools_time = time.time() - tools_start
            print(f"[BASE_DEBUG] A2A tools property access: {tools_time:.3f}s")
            
            # Commented out to avoid lazy evaluation delay during init
            # Tools will be discovered on-demand when actually used
            # logging_start = time.time()
            # print(f"[BASE_DEBUG] About to log {len(a2a_tools)} tools")
            # logger.info(f"A2A provider initialized with {len(a2a_tools)} tools")
            # for i, tool in enumerate(a2a_tools):
            #     tool_start = time.time()
            #     logger.info(f"A2A tool: {tool.name if hasattr(tool, 'name') else str(tool)}")
            #     tool_time = time.time() - tool_start
            #     if tool_time > 0.1:
            #         print(f"[BASE_DEBUG] Tool {i} logging took: {tool_time:.3f}s")
            # logging_time = time.time() - logging_start
            # print(f"[BASE_DEBUG] A2A tools logging: {logging_time:.3f}s")
            logger.info("A2A provider initialized (tool discovery deferred)")
        except Exception as e:
            logger.error(f"A2A provider initialization failed: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            logger.info("Continuing without A2A tools...")
        
        a2a_time = time.time() - a2a_start
        print(f"[BASE_DEBUG] A2A client setup: {a2a_time:.3f}s")
        
        # Combine all tools: A2A + provided + context
        combine_start = time.time()
        
        # Create shared org profile tool
        from strands import tool as strands_tool
        @strands_tool
        def get_org_profile(project_id: str) -> str:
            """Read the organization profile associated with a project.
            
            Returns the full org profile content (markdown) including: industry, size,
            jurisdictions, frameworks, risk appetite, crown jewels, security maturity,
            threat landscape, vendors, incidents, and audit findings.
            
            Args:
                project_id: The project ID to get the associated org profile for
            """
            try:
                # Get project to find profile_id
                project_result = self._invoke_lambda('risk-agent-projects', {
                    'requestContext': {'http': {'method': 'GET'}},
                    'pathParameters': {'id': project_id}
                })
                
                profile_id = None
                if isinstance(project_result, dict):
                    profile_id = project_result.get('profile_id')
                elif isinstance(project_result, list) and project_result:
                    profile_id = project_result[0].get('profile_id')
                
                if not profile_id:
                    return "No organization profile is linked to this project. Proceed with available information."
                
                # Read profile via get_profile Lambda
                profile_result = self._invoke_lambda('risk-agent-get_profile', {
                    'requestContext': {'http': {'method': 'GET'}},
                    'pathParameters': {'id': profile_id}
                })
                
                if isinstance(profile_result, dict):
                    profile_content = profile_result.get('content', '')
                    if profile_content:
                        return profile_content
                    return f"Profile {profile_id} found but has no content."
                
                return f"Could not retrieve profile {profile_id}."
            except Exception as e:
                return f"Could not read org profile: {str(e)}"
        
        all_tools = a2a_tools + (tools or []) + [clear_context_tool, summarize_context_tool, get_org_profile]
        combine_time = time.time() - combine_start
        print(f"[BASE_DEBUG] Tools combined: {combine_time:.3f}s")
        
        # Prepare trace attributes for Langfuse integration
        trace_start = time.time()
        trace_attributes = {}
        if langfuse_enabled:
            trace_attributes = {
                "langfuse.session_id": f"{agent_name.lower()}_session",
                "langfuse.user_id": "system",
                "langfuse.tags": [agent_name, "RiskAgent", "Strands-SDK"]
            }
        trace_time = time.time() - trace_start
        print(f"[BASE_DEBUG] Trace attributes prepared: {trace_time:.3f}s")
        
        # Create Strands Agent with unique agent_id and conversation manager
        agent_create_start = time.time()
        from strands.handlers.callback_handler import null_callback_handler
        self.agent = Agent(
            name=f"{agent_name} Agent",
            description=f"{agent_name} agent for risk assessment workflows",
            system_prompt=system_prompt,
            model=bedrock_model,
            tools=all_tools,
            callback_handler=null_callback_handler,
            conversation_manager=SlidingWindowConversationManager(window_size=10),
            agent_id=agent_name,  # Set unique agent_id for session management
            trace_attributes=trace_attributes if trace_attributes else None
        )
        agent_create_time = time.time() - agent_create_start
        print(f"[BASE_DEBUG] Strands Agent created: {agent_create_time:.3f}s")
        
        total_time = time.time() - base_init_start
        print(f"[BASE_DEBUG] BaseAgent.__init__ total: {total_time:.3f}s")
    
    def _load_system_prompt(self, key: str) -> str:
        """Load system prompt from S3"""
        try:
            bucket_name = os.getenv('APP_DATA_BUCKET')
            s3_client = boto3.client('s3')
            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=key
            )
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to load system prompt from {key}: {e}")
            return f"You are the {self.agent_name} agent."
    
    def _invoke_lambda(self, function_name: str, payload: dict) -> dict:
        """Invoke Lambda function with error handling"""
        try:
            from decimal import Decimal
            class DecimalEncoder(json.JSONEncoder):
                def default(self, o):
                    if isinstance(o, Decimal):
                        return int(o) if o == int(o) else float(o)
                    return super().default(o)
            
            logger.info(f"Invoking Lambda {function_name} with payload: {json.dumps(payload, indent=2, cls=DecimalEncoder)}")
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(payload, cls=DecimalEncoder)
            )
            result = json.loads(response['Payload'].read())
            logger.info(f"Lambda {function_name} response: {json.dumps(result, indent=2)}")
            
            # Handle nested body responses
            if 'body' in result:
                if isinstance(result['body'], str):
                    result = json.loads(result['body'])
                else:
                    result = result['body']
        
            return result
        except Exception as e:
            logger.error(f"Lambda invocation failed for {function_name}: {e}")
            return {"error": str(e)}
    
    def _refresh_bedrock_model(self):
        """Refresh bedrock model with new credentials"""
        try:
            from agents.shared.auto_refresh_credentials import create_auto_refreshing_session
            from strands.models import BedrockModel
            
            new_model = BedrockModel(
                model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
                temperature=0.0,
                max_tokens=40000,
                boto_session=create_auto_refreshing_session(self.agent_name)
            )
            self.agent.model = new_model
            logger.info(f"Bedrock model refreshed for {self.agent_name}")
        except Exception as e:
            logger.error(f"Failed to refresh bedrock model: {e}")
    
    def create_session_manager(self, session_id: str, user_id: str = None):
        """Create a Strands RepositorySessionManager with DynamoDB backend"""
        try:
            print(f"DEBUG: BaseAgent.create_session_manager - agent: {self.agent_name}, session_id: {session_id}, user_id: {user_id}")
            repository = DynamoDBSessionRepository()
            # Set user_id in repository using the new method
            if user_id:
                repository.set_current_user_id(user_id)
            print(f"DEBUG: Repository created with user_id: {user_id}")
            return RepositorySessionManager(session_id, repository)
        except Exception as e:
            logger.warning(f"Failed to create session manager: {e}")
            return None
    

    def _cleanup_orphaned_tool_use(self):
        """Remove tool_use blocks from conversation history that lack corresponding toolResult."""
        messages = self.agent.messages
        # Collect all tool_use ids that have a corresponding toolResult
        result_ids = set()
        for msg in messages:
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and "toolResult" in block:
                        result_ids.add(block["toolResult"].get("toolUseId"))
        # Remove orphaned tool_use blocks from assistant messages
        for msg in messages:
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                msg["content"] = [
                    block for block in msg["content"]
                    if not (isinstance(block, dict) and "toolUse" in block and block["toolUse"].get("toolUseId") not in result_ids)
                ]
        # Remove empty assistant messages
        self.agent.messages = [m for m in messages if m.get("content")]
        logger.info(f"Cleaned conversation history, {len(self.agent.messages)} messages remaining")

    def __call__(self, message: str, session_id: str = None, user_id: str = None):
        """Process message through the agent with optional session state"""
        import time
        start_time = time.time()
        logger.info(f"[{self.agent_name.upper()}] Agent called with session_id: {session_id}")
        
        # Handle context clearing
        if message.startswith("CLEAR_CONTEXT:"):
            self.agent.messages.clear()
            logger.info("Context cleared for new project session")
            return "Context cleared successfully"
        
        # Create session manager if session provided (but don't let it block processing)
        session_manager = None
        if session_id and user_id:
            try:
                logger.info(f"Creating session manager for session_id: {session_id}, user_id: {user_id}")
                session_manager = self.create_session_manager(session_id, user_id)
                if session_manager:
                    logger.info(f"Registering session hooks")
                    session_manager.register_hooks(self.agent.hooks)
                    logger.info(f"Initializing session")
                    session_manager.initialize(self.agent)
                    logger.info(f"Session management initialized for session_id: {session_id}")
                else:
                    logger.warning(f"Failed to create session manager, proceeding without session")
            except Exception as e:
                logger.error(f"Session management failed: {e}, proceeding without session")
                session_manager = None
        
        try:
            logger.info(f"Calling agent with message: {message[:100]}...")
            result = self.agent(message)
            logger.info(f"[{self.agent_name.upper()}] Response time: {time.time() - start_time:.2f}s")
            self._flush_langfuse_traces()
            return result
        except Exception as e:
            error_str = str(e).lower()
            # Handle orphaned tool_use blocks in conversation history
            if 'toolresult' in error_str or 'tool_result' in error_str or 'tooluse' in error_str:
                logger.warning(f"Orphaned tool_use detected, cleaning conversation history and retrying")
                self._cleanup_orphaned_tool_use()
                try:
                    result = self.agent(message)
                    logger.info(f"[{self.agent_name.upper()}] Response time (after cleanup): {time.time() - start_time:.2f}s")
                    self._flush_langfuse_traces()
                    return result
                except Exception as retry_e:
                    logger.error(f"Retry after cleanup failed: {retry_e}")
                    raise retry_e
            # Handle token expiration by refreshing credentials
            if 'expired' in error_str or 'token' in error_str:
                logger.warning(f"Token expired, refreshing after {time.time() - start_time:.2f}s")
                self._refresh_bedrock_model()
                result = self.agent(message)
                logger.info(f"[{self.agent_name.upper()}] Response time (after refresh): {time.time() - start_time:.2f}s")
                self._flush_langfuse_traces()
                return result
            logger.error(f"[{self.agent_name.upper()}] Error after {time.time() - start_time:.2f}s: {str(e)}")
            self._flush_langfuse_traces()
            raise e
        finally:
            self._flush_langfuse_traces()
    
    def _flush_langfuse_traces(self):
        """Flush Langfuse traces to ensure they are sent"""
        try:
            if is_enabled():
                flush()
                logger.debug("Langfuse traces flushed")
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse traces: {e}")