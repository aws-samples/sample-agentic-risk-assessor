# RiskAgent.Agentic - Pure AWS Strands Implementation

## Overview
RiskAgent.Agentic is a distributed AI agent system built with pure AWS Strands SDK that provides comprehensive security and risk assessment for AWS infrastructure.

## Architecture
```
Frontend (React.js) → API Gateway → A2A Load Balancer → 5 Individual Agent Tasks → Lambda Tools
```

### ECS Deployment Model
- **5 Separate ECS Tasks** (one per agent)
- **Independent scaling** and fault isolation
- **Optimized resource allocation** per agent workload

## Agents

### 1. Orchestrator Agent (Port 9001)
- **Tools**: projects Lambda wrapper, workflow coordination
- **Function**: Coordinates complete risk assessment workflow via A2A

### 2. Architect Agent (Port 9002)  
- **Tools**: diagram_analysis Lambda wrapper, projects Lambda wrapper
- **Function**: Analyzes architecture diagrams and categorizes AWS components

### 3. Risk Framework Agent (Port 9003)
- **Tools**: invoke_bedrock, process_service_controls, read_services Lambda wrappers
- **Function**: Maps security frameworks to AWS services with batch processing (replaces Step Functions)

### 4. Security Architect Agent (Port 9004)
- **Tools**: process_node_controls, get_node_details, invoke_bedrock Lambda wrappers  
- **Function**: Assigns controls to nodes with sequential processing (replaces Step Functions)

### 5. Risk Assessment Agent (Port 9005)
- **Tools**: get_node_controls, get_node_details, process_bedrock_results Lambda wrappers
- **Function**: Analyzes control coverage and calculates risk scores

## Key Features

### 100% Asset Reuse
- All existing Lambda functions wrapped as Strands tools
- No changes to frontend or database
- Preserves all original RiskAgent functionality

### Pure Strands Implementation
- No custom MCP code
- Native A2A communication
- Standardized tool patterns
- Built-in error handling and retry

### A2A Agent Discovery
- Automatic agent discovery via agent cards
- Load balancer routing to agent endpoints
- Configuration-based URL management
- Support for local and production environments

### Step Function Replacement
- Risk Framework Agent: Batch processing (MaxConcurrency=3)
- Security Architect Agent: Sequential processing (MaxConcurrency=1)
- Maintains original timing and retry logic

## Getting Started

### Prerequisites
```bash
pip install -r requirements.txt
```

### Local Development
```bash
# Start all agents
python main.py

# Run tests
pytest tests/
```

### Agent Communication
```python
# Example: Start risk assessment via A2A
from strands.multiagent.a2a import A2AClient
from agents.shared.a2a_discovery import get_agent_urls

# Get known agent URLs for discovery
known_urls = get_agent_urls(local=True)  # or local=False for production
client = A2AClient(known_agent_urls=known_urls)
result = await client.invoke_agent(
    "orchestrator", 
    "start_risk_assessment project-123 nist"
)
```

### A2A Agent Discovery

Agents are discoverable via their agent cards exposed at base URLs:

```yaml
# config/a2a_discovery.yaml
agents:
  orchestrator:
    url: "http://<YOUR_INTERNAL_ALB_DNS>/orchestrator"
    description: "Coordinates complete risk assessment workflow"
  architect:
    url: "http://<YOUR_INTERNAL_ALB_DNS>/architect"
    description: "Analyzes architecture diagrams and categorizes AWS components"
```

The orchestrator agent includes A2A client tools for automatic discovery:

```python
# Orchestrator can discover and communicate with other agents
response = agent("pick an agent and make a sample call")
```

## Testing

### Unit Tests
```bash
pytest tests/unit/
```

### Integration Tests  
```bash
pytest tests/integration/
```

## Deployment

**📋 For complete deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)**

### Quick Start - Staging Deployment

```bash
# Step 1: Build Lambda packages
bash infra/scripts/deploy_lambdas_unified.sh all build <your-aws-profile>

# Step 2: Deploy infrastructure
cd infra/environments/staging
bash terraform-wrapper.sh apply

# Step 3: Deploy Lambda code
cd ../../..
bash infra/scripts/deploy_lambdas_unified.sh all deploy <your-aws-profile>

# Step 4: Deploy agents
ENVIRONMENT=staging bash agents/deploy/deploy_ecs.sh all

# Step 5: Deploy frontend
cd frontend && npm run build && bash deploy_frontend.sh
```

### Deployment Architecture

The system deploys as 6 separate containerized A2A servers on AWS ECS/Fargate:

- **Orchestrator Task**: 256 CPU, 512 MB (Port 9001)
- **Architect Task**: 256 CPU, 512 MB (Port 9002)
- **Risk Framework Task**: 512 CPU, 1024 MB (Port 9003)
- **Security Architect Task**: 256 CPU, 512 MB (Port 9004)
- **Risk Assessment Task**: 256 CPU, 512 MB (Port 9005)
- **Auditor Task**: 256 CPU, 512 MB (Port 9006)

## Migration Benefits

1. **Eliminated Custom Code**: Pure Strands SDK implementation
2. **Enhanced Reliability**: Production-tested framework with built-in fault tolerance
3. **Better Performance**: Optimized A2A communication
4. **Improved Monitoring**: Native observability features
5. **Standards Compliance**: A2A protocol for interoperability

## Status: Ready for Production 🚀