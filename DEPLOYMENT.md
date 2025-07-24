# RiskAgent.Agentic Deployment Guide

# 1. Prerequisites

## Required Tools
- **Terraform** >= 1.5
- **Docker Desktop** (must be running)
- **AWS CLI** >= 2.0
- **Python** 3.11+
- **Node.js** 18+

## Windows Users - WSL Setup

The deployment scripts are written for Unix/Linux environments and require WSL (Windows Subsystem for Linux) to run on Windows.

### Installing WSL

**For Windows 10 (version 2004+) and Windows 11:**
```powershell
# Open PowerShell as Administrator and run:
wsl --install
```
This installs Ubuntu by default. Restart your computer when prompted.

### Setting Up WSL for Deployment

**1. Launch WSL Environment**
```bash
# From Windows Command Prompt, PowerShell, or Start Menu:
wsl
# Or launch "Ubuntu" from Start Menu
```

**2. Install Required Tools**
```bash
# Update package manager
sudo apt update

# Install deployment dependencies
sudo apt install python3 python3-pip curl zip unzip

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Verify installations
python3 --version
aws --version
```

**3. Navigate to Your Project**
```bash
# Windows drives are mounted under /mnt/
# Example: C:\Users\YourName\Documents\risk-agent-core becomes:
cd /mnt/c/Users/YourName/Documents/risk-agent-core

# Make scripts executable
chmod +x infra/scripts/deploy_lambdas_unified.sh
chmod +x agents/deploy/deploy_ecs.sh
chmod +x frontend/deploy_frontend.sh
```

**4. Configure AWS in WSL**
```bash
# Configure AWS CLI (same as Windows)
aws configure --profile <your-aws-profile>

# Set environment variables for deployment
export AWS_PROFILE=<your-aws-profile>
export ENVIRONMENT=staging  # or dev/prod
```

**5. Run Deployment Commands**
All deployment commands from this guide work exactly as written in WSL:
```bash
# Example: Deploy all Lambda functions
./infra/scripts/deploy_lambdas_unified.sh all both

# Example: Deploy agents
./agents/deploy/deploy_ecs.sh --clean all
```

### WSL Tips for Windows Users

**File Access**: Your Windows files are accessible at `/mnt/c/`, `/mnt/d/`, etc.

**Performance**: For better performance, consider copying your project to WSL's native filesystem:
```bash
# Copy to WSL home directory
cp -r /mnt/c/path/to/risk-agent-core ~/risk-agent-core
cd ~/risk-agent-core
```

**VS Code Integration**: Install the "WSL" extension in VS Code to edit files directly in WSL environment.

**Environment Persistence**: WSL maintains your environment between sessions. Set AWS_PROFILE once and it persists.

### Docker Setup
Install Docker Desktop from https://www.docker.com/products/docker-desktop/
Start Docker Desktop application and verify Docker is running.
```bash
docker --version
docker ps
```

## AWS Configuration
```bash
# Configure AWS CLI
aws configure --profile <your-aws-profile>

# Verify access
aws sts get-caller-identity --profile <your-aws-profile>
```

# 2. Setup
## 2.1 Clone the repo and install Frontend dependencies

```bash
git clone https://github.com/aws-samples/sample-agentic-risk-assessor.git
cd risk-agent-core
# Install frontend dependencies
cd frontend && npm install && cd ..
```

## 2.2 Manual Terraform Configuration

### Edit bootstrap `terraform.tfvars` 
---
Create the `infra/bootstrap/terraform.tfvars` file. Using `terraform.tfvars.example` as a template create your own version substituting the values defined below.

```bash
aws_account_id = "<your-aws-account-id>"
aws_profile    = "<your-aws-profile>"
region         = "us-east-1"
project_name   = "risk-agent"

terraform_state_bucket = "risk-agent-terraform-state-<your-aws-account-id>"
terraform_locks_table  = "risk-agent-terraform-locks-<your-aws-account-id>"
```


### Edit environment-specific `terraform.tfvars ` 
---
Create the `infra/environments/staging/terraform.tfvars` file.  Using `terraform.tfvars.example` as a template create your own version substituting the values defined below.


```bash
# Environment Configuration
aws_account_id = "<your-aws-account-id>"
aws_profile = "<your-aws-profile>"

# Regional Configuration
region = "us-east-1"

# Project Configuration:
project_name = "risk-agent" 
environment = "staging"

# Terraform state backend names (bootstrap will create these):
terraform_state_bucket = "risk-agent-terraform-state-<your account id>"
terraform_locks_table = "risk-agent-terraform-locks-<your account id>"

# Cognito Configuration:
cognito_callback_urls = [
  "http://localhost:3000/auth/callback"  # Add production URLs as needed
]
cognito_logout_urls = [
  "http://localhost:3000/"  # Add production URLs as needed
]

# Lambda Functions - Defined in Lambda module

# Langfuse Integration - SaaS with OpenTelemetry
langfuse_enabled = false
langfuse_saas_enabled = true
langfuse_saas_host = "https://us.cloud.langfuse.com"

# Cross-account Bedrock configuration (if using different account):
bedrock_role_arn = "arn:aws:iam::<bedrock-account-id>:role/<bedrock-role-name>"
bedrock_account_id = "<bedrock-account-id>"
bedrock_model_id = "<model-id>"  # e.g., us.anthropic.claude-sonnet-4-20250514-v1:0
bedrock_role_name = "<bedrock-role-name>"
bedrock_max_tokens = 40000
bedrock_temperature = 0.0
bedrock_top_p = 0.1
bedrock_top_k = 1
bedrock_timeout = 120

# API Gateway (leave empty - auto-populated):
api_gateway_routes = {}
```


### Edit `backend.hcl` 
---
Create the `backend.hcl` file. Using `infra/environments/<environment name>/backend.hcl` file as a template create your own version substituting the values defined below.

```bash
bucket         = "risk-agent-terraform-state-<your-aws-account-id>"
key            = "terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "risk-agent-terraform-locks-<your-aws-account-id>"
encrypt        = true
```

## 2.3 Set ENV variables

**Set AWS profile for agent deployment**
`export AWS_PROFILE=<your-aws-profile>`

# 3. 🆕 First-Time Deployment (New AWS Account)

**Prerequisites**: Fresh AWS account with no existing RiskAgent infrastructure
**⚠️ Critical**: Run steps in exact order. Step 2 creates Lambda function code, Step 3 creates the lambda infrastructure, step 4 deploys code to them.  


**Step 1: Bootstrap Terraform Backend** (One-time setup)
Creates S3 bucket and DynamoDB table for Terraform state management.  
```bash
# Create S3 bucket and DynamoDB table for Terraform state
cd infra/bootstrap
terraform init
terraform apply -auto-approve

# Verify backend resources created
aws s3 ls | grep terraform-state
aws dynamodb list-tables | grep terraform-locks
cd ../.. # Return to project root dir
```

**Step 2: Build Lambda Packages**
Builds ZIP files (needed for Terraform)

`chmod +x ./infra/scripts/deploy_lambdas_unified.sh`
`./infra/scripts/deploy_lambdas_unified.sh all build`

Note: Show script help with --help flag
`./infra/scripts/deploy_lambdas_unified.sh --help` or simply `./infra/scripts/deploy_lambdas_unified.sh`

**Step 3: Deploy Infrastructure**
```bash
cd infra/environments/staging
chmod +x ./terraform-wrapper.sh
./terraform-wrapper.sh init
./terraform-wrapper.sh plan
./terraform-wrapper.sh apply -auto-approve
cd ../../.. # Return to project root
```

**Step 4: Deploy Lambda Code**
Updates the existing functions with application code. This takes around 80-90 minutes.
`./infra/scripts/deploy_lambdas_unified.sh all deploy`

**Step 5: Deploy Agents**

```bash
# Ensure Docker Desktop is running first
docker ps  # Should not error

# Deploy agents with AWS profile 
chmod +x ./agents/deploy/deploy_ecs.sh
./agents/deploy/deploy_ecs.sh --clean all
```

Note: Show script help with --help flag
`./agents/deploy/deploy_ecs.sh --help` or simply `./agents/deploy/deploy_ecs.sh`

**Step 6: Deploy Frontend**
Frontend now deployed via Terraform ECS (separate cluster)
Build and push image:
`./frontend/deploy_frontend.sh`


**Step 7: Setup Langfuse SaaS (Optional - for Observability & Evaluation)**
1. Create Langfuse Cloud account at https://cloud.langfuse.com
2. Create a new project and get API keys
3. Update terraform.tfvars with Langfuse credentials:  


# Edit infra/environments/staging/terraform.tfvars. 
```bash
langfuse_saas_enabled = true
langfuse_saas_host = "https://us.cloud.langfuse.com"  # or https://cloud.langfuse.com for EU
```
# 4. Update main.tf with your actual API keys:
# Edit infra/environments/staging/main.tf
```bash
langfuse_saas_public_key = "pk-lf-your-public-key"
langfuse_saas_secret_key = "sk-lf-your-secret-key"
```
# 5. Apply infrastructure changes to enable telemetry:
`.infra/environments/staging/terraform-wrapper.sh apply`

# 6. Redeploy agents to pick up new telemetry configuration:
`./agents/deploy/deploy_ecs.sh all`

# 7. Verify traces appear in Langfuse dashboard after agent interactions


# 4. 🔄 Code Updates (Existing Environment)

## Lambda Code Updates Only
Build and deploy Lambda code changes - AWS_PROFILE required if not already an ENV variable.  Beware building and deploying all Lambdas take over 90 minutes. Consider building and deploying lambdas individually as needed.

`./infra/scripts/deploy_lambdas_unified.sh all both <your-aws-profile>`


## Upload system prompts if changed
This does NOT redeploy lambda - AWS_PROFILE required if not already an ENV variable
`./infra/scripts/deploy_lambdas_unified.sh prompts deploy <your-aws-profile>`


## Agent Code Updates Only

**Deploy agent changes**
`./agents/deploy/deploy_ecs.sh --clean all <your-aws-profile>`

**For a single agent - for example**
`./agents/deploy/deploy_ecs.sh --clean risk_assessment <your-aws-profile>`


## Frontend Updates Only

`cd frontend && npm run build && ./deploy_frontend.sh`


**Infrastructure Changes**:
If Terraform files changed
`./infra/environments/staging/terraform-wrapper.sh apply`

# 5. Architecture

**Agents**: 4 ECS Tasks on `risk-agent-agents` cluster - Architect (9002), Security Architect (9004), Risk Assessment (9005), Auditor (9006)

**Frontend**: 1 ECS Task on `risk-agent-frontend` cluster - Next.js app (3000)

**Infrastructure**: 
- **Compute**: 2 separate ECS clusters (agents + frontend)
- **Storage**: DynamoDB tables, S3 buckets
- **Networking**: VPC, security groups, API Gateway
- **Auth**: Cognito User Pool
- **State**: S3 + DynamoDB for Terraform backend

**Modules**: Separate Terraform modules for cognito, dynamodb, s3, networking, iam, lambda, api-gateway, ecs (agents), frontend

# 6. Local Development

### Frontend Local Development

To run the frontend locally with proper environment configuration:

**Step 1: Setup Local Environment**
```bash
# Generate .env.local from terraform outputs (no hardcoding)
cd frontend
AWS_PROFILE=<your-aws-profile> ENVIRONMENT=staging ./setup-local-env.sh
```

**Step 2: Start Development Server**
```bash
# Install dependencies (if not done already)
npm install

# Start local development server
npm run dev
```

**Step 3: Create User Account**
```bash
# Option 1: Use signup page
# Navigate to http://localhost:3000/signup
# Create account and verify email

# Option 2: Create user via AWS CLI
aws cognito-idp admin-create-user \
  --user-pool-id <user-pool-id> \
  --username testuser@example.com \
  --user-attributes Name=email,Value=testuser@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id <user-pool-id> \
  --username testuser@example.com \
  --password YourPassword123! \
  --permanent
```

**Local Environment Variables**:
- `NEXT_PUBLIC_COGNITO_USER_POOL_ID` - From terraform output
- `NEXT_PUBLIC_COGNITO_CLIENT_ID` - From terraform output  
- `NEXT_PUBLIC_API_URL` - From terraform output
- `NEXT_PUBLIC_CLOUDFRONT_URL` - From terraform output
- `NEXT_PUBLIC_AGENTS_URL` - From terraform output

**⚠️ Important**: Never hardcode values in `.env.local`. Always use the setup script to pull from terraform outputs.

# 7. Troubleshooting

**First-Time Deployment Issues**:
If terraform init fails with backend errors:
1. Check AWS credentials
`aws sts get-caller-identity --profile <your-aws-profile>`

2. Run bootstrap process first
```bash
cd infra/bootstrap
terraform init
terraform apply -auto-approve
cd ../.. # Return tp project root
```

3. Update bootstrap/terraform.tfvars with correct account ID and profile.  

4. Re-run main deployment.  
```bash
cd ../environments/staging/
./terraform-wrapper.sh init <your-aws-profile>
```

**State Lock Errors**: Run bootstrap process first to create backend resources properly.

**Docker Daemon Not Running**:
```bash
# Start Docker Desktop application
open -a Docker
# Wait for Docker to start, then verify:
docker ps
```

**SSL Errors**: Always use wrapper scripts (`terraform-wrapper.sh`, not `terraform`)

**Lambda Functions Skipped**: Run Step 2 - build, Step 3 - infrastructure, then Step 4 (Lambda deploy)

**Agent Deployment Fails**: Ensure Docker Desktop is running and AWS profile is set

**Check Deployment**:
```bash
# Verify infrastructure
cd infra/environments/staging
./terraform-wrapper.sh output

# Check Lambda functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `risk-agent`)].FunctionName'

# Check ECS services
aws ecs list-services --cluster risk-agent-agents-staging
```

**Rollback**:
```bash
# Infrastructure
cd infra/environments/staging
git checkout <previous-commit>
bash terraform-wrapper.sh apply

# Agents
ENVIRONMENT=staging IMAGE_TAG=<previous-tag> bash agents/deploy/deploy_ecs.sh all
```

## Word Document Processing Issues

**Word Document Upload 500 Error (CORS Preflight)**:
```bash
# Symptom: Word document upload fails with 500 Internal Server Error on OPTIONS request
# Root Cause: Missing pypandoc Python package in pandoc layer

# Check CloudWatch logs for process_word_document Lambda:
aws logs filter-log-events --log-group-name /aws/lambda/risk-agent-process-word-document --filter-pattern "No module named 'pypandoc'"

# Fix: Rebuild pandoc layer with pypandoc
bash infra/scripts/deploy_lambdas_unified.sh pandoc build <your-aws-profile>
bash infra/scripts/deploy_lambdas_unified.sh pandoc deploy <your-aws-profile>

# Update Lambda to use new layer version
cd infra/environments/staging
bash terraform-wrapper.sh apply
```

**Word Document Processing Failures**:
```bash
# Symptom: Word documents not processed correctly or routing errors
# Check API Gateway routing:
aws apigateway get-resources --rest-api-id <api-id> --query 'items[?pathPart==`upload-word-document`]'

# Verify Lambda function exists:
aws lambda get-function --function-name risk-agent-process-word-document

# Check pandoc layer attachment:
aws lambda get-function --function-name risk-agent-process-word-document --query 'Configuration.Layers[?contains(LayerArn, `pandoc`)]'
```

**Missing System Prompts (Agent Startup)**:
```bash
# Symptom: Agents fail to start with S3 key not found errors
# Check S3 bucket contents:
aws s3 ls s3://risk-agent-app-data-<random-id>/agents/

# Upload missing system prompts:
aws s3 cp agents/architect/prompts/system_prompt.xml s3://risk-agent-app-data-<random-id>/agents/architect/system_prompt.xml
aws s3 cp agents/auditor/prompts/system_prompt.xml s3://risk-agent-app-data-<random-id>/agents/auditor/system_prompt.xml
```

**Step Functions Execution Failures (Missing Framework Prompts)**:
```bash
# Symptom: Step Functions stuck in RUNNING state, Lambda returns "Prompt not found for framework nist"
# Check CloudWatch logs:
aws logs filter-log-events --log-group-name /aws/lambda/risk-agent-process-service-controls --filter-pattern "NoSuchKey"

# Check S3 bucket for system prompts:
aws s3 ls "s3://risk-agent-app-data-<random-id>/system prompts/"

# Upload missing system prompts:
bash infra/scripts/deploy_lambdas_unified.sh prompts deploy <your-aws-profile>

# Verify upload:
aws s3 ls "s3://risk-agent-app-data-<random-id>/system prompts/" --profile <your-aws-profile>
# Should show: MappingPrompts.json, ControlMappingPrompt.json, FrameworkConfig.json
```