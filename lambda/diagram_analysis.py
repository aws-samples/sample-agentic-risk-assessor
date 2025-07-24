# Standard library imports
import base64
import json
import logging
import os
import traceback
from datetime import datetime
import sys
from typing import Dict, List, Optional, Any, Union

sys.path.append('/opt/python')  # For Lambda layers
sys.path.append('.')            # For local modules like shared/

from shared.base_lambda import BaseLambda

# Third-party imports
import boto3
import instructor
from pydantic import BaseModel, Field, computed_field

# Configure logging for AWS Lambda
logger = logging.getLogger(__name__)

# Set log level from environment variable with fallback to INFO
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
try:
    logger.setLevel(getattr(logging, log_level))
except AttributeError:
    logger.setLevel(logging.INFO)
    logger.warning(f"Invalid LOG_LEVEL '{log_level}', defaulting to INFO")


# Pydantic models for structured output
class DiagramNode(BaseModel):
    """Represents a node/component in the architecture diagram"""
    id: str = Field(description="Unique identifier for the node")
    type: str = Field(description="AWS service name (e.g., 'S3', 'Lambda'), 'generic' for non-AWS components, or 'unknown' if the service cannot be clearly identified")
    name: str = Field(description="Display name or label of the component")
    description: str = Field(description="Brief description of the component's purpose")

class DiagramFlow(BaseModel):
    """Represents a connection/flow between nodes in the diagram"""
    id: str = Field(description="Unique identifier for the flow")
    source: str = Field(description="ID of the source node")
    target: str = Field(description="ID of the target node")
    type: str = Field(description="Type of connection (e.g., 'data flow', 'API call')")
    description: str = Field(description="Description of what flows through this connection")

class DiagramAnalysis(BaseModel):
    """Complete analysis of an AWS architecture diagram"""
    nodes: List[DiagramNode] = Field(description="All components/nodes identified in the diagram")
    flows: List[DiagramFlow] = Field(description="All connections/flows between nodes")
    
    @computed_field
    @property
    def get_node_count(self) -> int:
        """Returns the total number of nodes in the diagram"""
        return len(self.nodes)


class AWSClients:
    """Manages AWS service clients."""
    
    def __init__(self, dynamodb=None, s3=None, projects_table=None) -> None:
        # Use base class defaults or provided values
        self.dynamodb = dynamodb or boto3.resource('dynamodb')
        self.s3 = s3 or boto3.client('s3')
        
        # Use base class documents_bucket if available, otherwise get from env
        if hasattr(self, 'documents_bucket'):
            self.documents_bucket = getattr(self, 'documents_bucket', self._get_required_env('DOCUMENTS_BUCKET'))
        else:
            self.documents_bucket: str = self._get_required_env('DOCUMENTS_BUCKET')
            
        # Load and validate remaining mandatory environment variables
        self.diagrams_bucket: str = self._get_required_env('DIAGRAMS_BUCKET')
        self.diagram_analysis_table: str = self._get_required_env('DIAGRAM_ANALYSIS_TABLE')
        self.bedrock_model_id: str = self._get_required_env('BEDROCK_MODEL_ID')
        
        # Optional environment variables for cross-account Bedrock access
        self.bedrock_account_id: Optional[str] = os.environ.get('BEDROCK_ACCOUNT_ID')
        self.bedrock_role_name: Optional[str] = os.environ.get('BEDROCK_ROLE_NAME')
        self.bedrock_region: str = os.environ.get('BEDROCK_REGION', 'us-east-1')
        
        # Initialize Bedrock-specific clients
        self.bedrock_runtime: Optional[boto3.client] = self._initialize_bedrock()
        self.instructor_client: Optional[instructor.Instructor] = self._initialize_instructor()

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise descriptive error."""
        value = os.environ.get(key)
        if not value:
            raise ValueError(f"Required environment variable '{key}' is not set or is empty")
        return value
    
    def _initialize_bedrock(self) -> Optional[boto3.client]:
        """Initialize Bedrock Runtime client with optional cross-account access.
        
        This method creates a Bedrock Runtime client using one of two approaches:
        
        1. Cross-Account Access (when BEDROCK_ACCOUNT_ID is provided):
           - Uses AWS STS to assume a role in the target Bedrock account
           - Creates temporary credentials for secure cross-account access
           - Useful for centralized Bedrock deployments or cost management
        
        2. Local Account Access (when BEDROCK_ACCOUNT_ID is not provided):
           - Creates a standard Bedrock client using the current account's credentials
           - Uses the default credential chain (IAM role, environment variables, etc.)
        
        Returns:
            Optional[boto3.client]: Configured Bedrock Runtime client, or None if initialization fails.
                                   Failure is logged but doesn't raise exceptions to allow graceful degradation.
        
        Raises:
            Exception: Only during cross-account setup if BEDROCK_ROLE_NAME is missing.
        """
        try:
            if self.bedrock_account_id:
                return self._create_cross_account_bedrock(self.bedrock_account_id)
            else:
                bedrock_runtime: boto3.client = boto3.client('bedrock-runtime', region_name=self.bedrock_region)
                logger.info("Local Bedrock client initialized")
                return bedrock_runtime
                
        except Exception as e:
            logger.error(f"Error initializing Bedrock client: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def _create_cross_account_bedrock(self, bedrock_account_id: str) -> boto3.client:
        """Create cross-account Bedrock client."""
        sts_client: boto3.client = boto3.client('sts')
        
        if not self.bedrock_role_name:
            raise Exception("BEDROCK_ROLE_NAME environment variable not configured for cross-account access")
        
        role_arn: str = f"arn:aws:iam::{bedrock_account_id}:role/{self.bedrock_role_name}"
        
        assumed_role: Dict[str, Any] = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='diagram-analysis-bedrock-session'
        )
        
        credentials: Dict[str, str] = assumed_role['Credentials']
        bedrock_runtime: boto3.client = boto3.client(
            'bedrock-runtime',
            region_name=self.bedrock_region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        
        logger.info(f"Cross-account Bedrock client initialized for account {bedrock_account_id}")
        return bedrock_runtime

    def _initialize_instructor(self) -> Optional[instructor.Instructor]:
        """Initialize Instructor client from Bedrock Runtime client.
        
        Returns:
            Optional[instructor.Instructor]: Configured Instructor client, or None if Bedrock client is unavailable.
        """
        if not self.bedrock_runtime:
            logger.warning("Cannot initialize Instructor client: Bedrock client is not available")
            return None
        
        try:
            instructor_client = instructor.from_bedrock(client=self.bedrock_runtime)
            logger.info("Instructor client initialized successfully")
            return instructor_client
        except Exception as e:
            logger.error(f"Error initializing Instructor client: {str(e)}")
            logger.debug(traceback.format_exc())
            return None





class DiagramAnalyzer:
    """Handles diagram analysis using Bedrock."""
    
    def __init__(self, aws_clients: AWSClients) -> None:
        self.aws_clients: AWSClients = aws_clients
        self.bedrock_model_id: str = aws_clients.bedrock_model_id
        self.instructor_client: Optional[instructor.Instructor] = aws_clients.instructor_client
    
    def analyze(self, image_base64: str, document_text: str = "") -> Dict[str, Any]:
        """Analyze diagram and return structured data using Instructor.
        
        Args:
            image_base64: Base64 encoded image data
            document_text: Optional additional context document
            
        Returns:
            Dict containing nodes and flows, or empty structure if analysis fails
        """
        if not self.instructor_client:
            raise Exception("Instructor client not initialized")
        
        if not image_base64 or not image_base64.strip():
            logger.error("Image data is empty or invalid")
            return {"nodes": [], "flows": []}
        
        try:
            # Validate base64 format
            image_bytes = base64.b64decode(image_base64, validate=True)
        except Exception as e:
            logger.error(f"Invalid base64 image data: {str(e)}")
            return {"nodes": [], "flows": []}
        
        # Validate file size (10MB max)
        MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > MAX_IMAGE_SIZE:
            logger.error(f"Image exceeds maximum size: {len(image_bytes)} bytes (max {MAX_IMAGE_SIZE})")
            return {"error": "Image exceeds 10MB size limit", "nodes": [], "flows": []}
        
        prompt: str = self._create_prompt(document_text)

        logger.info(f"Calling Bedrock with Instructor using model: {self.bedrock_model_id}")
        logger.debug(f"Image base64 size: {len(image_base64)} bytes")

        try:
            # Use Instructor for structured output - no manual JSON parsing needed!
            response: DiagramAnalysis = self.instructor_client.messages.create(
                model=self.bedrock_model_id,
                max_tokens=4096,
                temperature=0,
                response_model=DiagramAnalysis,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": prompt
                            },
                            {
                                "image": {
                                    "format": "png",
                                    "source": {
                                        "bytes": image_bytes
                                    }
                                }
                            }
                        ]
                    }
                ]
            )
            
            logger.info("Bedrock API call with Instructor successful")
            logger.debug(f"Found {len(response.nodes)} nodes and {len(response.flows)} flows")
            
            # Convert Pydantic model to dict for compatibility with existing code
            return response.model_dump()
            
        except Exception as e:
            logger.error(f"Error during Instructor analysis: {str(e)}")
            logger.debug(traceback.format_exc())
            # Return empty structure on error
            return {"nodes": [], "flows": []}
  
    def _create_prompt(self, document_text: str) -> str:
        """Create analysis prompt optimized for Instructor structured output."""
        prompt = """Analyze this AWS architecture diagram and identify all components and connections.

IMPORTANT: If this image does NOT contain an architecture diagram or technical system diagram (e.g., it's a photo of people, landscapes, random objects, etc.), return empty lists for both nodes and flows.

If the image DOES contain architecture components, please:

1. Identify ALL components visible in the diagram:
   - Users or user groups
   - AWS services (S3, Lambda, API Gateway, etc.)
   - Bedrock agents and sub-agents
   - Knowledge bases and action groups
   - Any other technical components

2. Identify ALL connections and data flows:
   - API calls between services
   - Data flows and transfers
   - User interactions
   - Service-to-service communications

3. Requirements for IDs:
   - Each node must have a unique ID (node1, node2, etc.)
   - Each flow must have a unique ID (flow1, flow2, etc.)
   - Source and target in flows must reference valid node IDs

4. Be comprehensive and thorough - capture every visible component and connection."""
        
        if document_text:
            prompt += f"""

Additional context from project documentation:
{document_text}

Use this context to better understand the purpose and relationships of components in the diagram."""
        
        return prompt


class ProjectService:
    """Handles project operations."""
    
    def __init__(self, aws_clients: AWSClients) -> None:
        self.aws_clients: AWSClients = aws_clients
    

    
    def get_diagram_image(self, project: Dict[str, Any]) -> str:
        """Get diagram image from S3."""
        if 'diagram_filename' not in project:
            raise ValueError('Project has no diagram')
        
        s3_bucket: str = self.aws_clients.diagrams_bucket
        diagram_filename: str = project['diagram_filename']
        logger.debug(f"s3_bucket: {s3_bucket} - diagram: {diagram_filename}")
        
        try:
            s3_response: Dict[str, Any] = self.aws_clients.s3.get_object(Bucket=s3_bucket, Key=diagram_filename)
            image_data: bytes = s3_response['Body'].read()
            
            if not image_data:
                raise ValueError('Image file is empty')
            
            return base64.b64encode(image_data).decode('utf-8')
        except self.aws_clients.s3.exceptions.NoSuchKey:
            raise ValueError(f'Diagram file not found: {diagram_filename}')
        except self.aws_clients.s3.exceptions.NoSuchBucket:
            raise ValueError(f'Diagram bucket not found: {s3_bucket}')
        except Exception as e:
            raise ValueError(f'Failed to access diagram image: {str(e)}')
    
    def get_document_text(self, project: Dict[str, Any]) -> str:
        """Get document text from S3 if available."""
        if 'document_text_key' not in project:
            return ""
        
        try:
            text_response: Dict[str, Any] = self.aws_clients.s3.get_object(
                Bucket=self.aws_clients.documents_bucket,
                Key=project['document_text_key']
            )
            document_text: str = text_response['Body'].read().decode('utf-8')
            
            # Truncate if too long (limit to ~4000 tokens)
            if len(document_text) > 16000:
                document_text = document_text[:16000] + "...[Document truncated due to length]"
            
            return document_text
        except Exception as doc_err:
            logger.warning(f"Error retrieving document text: {str(doc_err)}")
            return ""


class AnalysisRepository:
    """Handles diagram analysis data persistence."""
    
    def __init__(self, aws_clients: AWSClients) -> None:
        self.table = aws_clients.dynamodb.Table(aws_clients.diagram_analysis_table)
    
    def get(self, project_id: str) -> Dict[str, Any]:
        """Get analysis from DynamoDB."""
        response: Dict[str, Any] = self.table.get_item(Key={'project_id': project_id})
        return response.get('Item', {'nodes': [], 'flows': []})
    
    def save(self, project_id: str, nodes: List[Dict[str, Any]], flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save analysis to DynamoDB."""
        analysis_item: Dict[str, Any] = {
            'project_id': project_id,
            'nodes': nodes,
            'flows': flows,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.table.put_item(Item=analysis_item)
        return analysis_item
    
    def update(self, project_id: str, nodes: Optional[List[Dict[str, Any]]] = None, flows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Update existing analysis."""
        current_item: Dict[str, Any] = self.get(project_id)
        
        update_item: Dict[str, Any] = {
            'project_id': project_id,
            'updated_at': datetime.now().isoformat()
        }
        
        if nodes is not None:
            update_item['nodes'] = nodes
        elif current_item and 'nodes' in current_item:
            update_item['nodes'] = current_item['nodes']
        else:
            update_item['nodes'] = []
            
        if flows is not None:
            update_item['flows'] = flows
        elif current_item and 'flows' in current_item:
            update_item['flows'] = current_item['flows']
        else:
            update_item['flows'] = []
            
        if current_item and 'created_at' in current_item:
            update_item['created_at'] = current_item['created_at']
        else:
            update_item['created_at'] = update_item['updated_at']
        
        self.table.put_item(Item=update_item)
        return update_item


class DiagramAnalysisHandler(BaseLambda):
    """Main handler for diagram analysis requests."""
    
    def __init__(self) -> None:
        super().__init__()
        self.aws_clients: AWSClients = AWSClients(
            dynamodb=self.dynamodb,
            s3=self.s3,
            projects_table=self.projects_table
        )
        self.analyzer: DiagramAnalyzer = DiagramAnalyzer(self.aws_clients)
        self.project_service: ProjectService = ProjectService(self.aws_clients)
        self.repository: AnalysisRepository = AnalysisRepository(self.aws_clients)
    
    def handle_get(self, project_id: str) -> Dict[str, Any]:
        """Handle GET request."""
        try:
            logger.info(f"Getting diagram analysis for project: {project_id}")
            analysis: Dict[str, Any] = self.repository.get(project_id)
            return self.success_response(analysis)
        except Exception as e:
            logger.error(f"Error getting diagram analysis: {str(e)}")
            return self.handle_error(f'Error retrieving diagram analysis: {str(e)}')
    
    def handle_post(self, project_id: str) -> Dict[str, Any]:
        """Handle POST request with structured analysis."""
        try:
            logger.info(f"Starting structured diagram analysis for project: {project_id}")
            project: Dict[str, Any] = self.get_project(project_id)
            
            try:
                image_base64: str = self.project_service.get_diagram_image(project)
            except ValueError as img_error:
                logger.warning(f"Image access error for project {project_id}: {str(img_error)}")
                # Return empty analysis without calling Bedrock
                analysis_item: Dict[str, Any] = self.repository.save(project_id, [], [])
                return self.success_response({
                    'message': f'Diagram analysis completed with empty results: {str(img_error)}',
                    'analysis': analysis_item
                })
            
            document_text: str = self.project_service.get_document_text(project)
            analysis_data: Dict[str, Any] = self.analyzer.analyze(image_base64, document_text)
            
            analysis_item: Dict[str, Any] = self.repository.save(
                project_id,
                analysis_data.get('nodes', []),
                analysis_data.get('flows', [])
            )
            
            logger.info(f"Structured analysis completed successfully for project: {project_id}")
            logger.debug(f"Analysis data: {json.dumps(analysis_item, default=str)}")
            return self.success_response({
                'message': 'Structured diagram analysis completed successfully',
                'analysis': analysis_item
            })
            
        except ValueError as e:
            logger.warning(f"Validation error for project {project_id}: {str(e)}")
            return self.handle_error(str(e), 404 if 'not found' in str(e).lower() else 400)
        except Exception as e:
            logger.error(f"Error analyzing diagram for project {project_id}: {str(e)}")
            return self.handle_error(f'Error analyzing diagram: {str(e)}')

    def handle_put(self, project_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PUT request."""
        try:
            logger.info(f"Updating diagram analysis for project: {project_id}")
            if 'nodes' not in body and 'flows' not in body:
                return self.handle_error('Request must include nodes or flows', 400)
            
            update_item: Dict[str, Any] = self.repository.update(
                project_id,
                body.get('nodes'),
                body.get('flows')
            )
            
            logger.info(f"Analysis updated successfully for project: {project_id}")
            return self.success_response({
                'message': 'Diagram analysis updated successfully',
                'analysis': update_item
            })
            
        except Exception as e:
            logger.error(f"Error updating diagram analysis for project {project_id}: {str(e)}")
            return self.handle_error(f'Error updating diagram analysis: {str(e)}')


# Initialize handler
analysis_handler: DiagramAnalysisHandler = DiagramAnalysisHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda function entry point."""
    logger.info(f"Event received: {json.dumps(event)}")
    
    # Handle OPTIONS request (CORS preflight)
    if event['requestContext']['http']['method'] == 'OPTIONS':
        return analysis_handler.handle_options()
    
    # Get HTTP method and project ID
    http_method: str = event['requestContext']['http']['method']
    path_params: Dict[str, Any] = event.get('pathParameters', {}) or {}
    project_id: Optional[str] = path_params.get('id')
    
    if not project_id:
        logger.warning("Request missing project ID")
        return analysis_handler.handle_error('Project ID is required', 400)
    
    logger.info(f"Processing {http_method} request for project: {project_id}")
    
    # Route to appropriate handler
    if http_method == 'GET':
        return analysis_handler.handle_get(project_id)
    elif http_method == 'POST':
        return analysis_handler.handle_post(project_id)
    elif http_method == 'PUT':
        body: Dict[str, Any] = json.loads(event['body'])
        return analysis_handler.handle_put(project_id, body)
    else:
        logger.warning(f"Method not allowed: {http_method}")
        return analysis_handler.handle_error('Method not allowed', 405)
