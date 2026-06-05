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
cd /mnt/c/Users/YourName/Documents/risk-agent-core

# Make scripts executable
chmod +x infra/scripts/deploy_lambdas_unified.sh
chmod +x agents/deploy/deploy_ecs.sh
chmod +x frontend/deploy_frontend.sh
```

**4. Configure AWS in WSL**
```bash
aws configure --profile <your-aws-profile>
export AWS_PROFILE=<your-aws-profile>
export ENVIRONMENT=staging
```

**5. Run Deployment Commands**
All deployment commands from this guide work exactly as written in WSL.

### WSL Tips

- **File Access**: Windows files at `/mnt/c/`, `/mnt/d/`, etc.
- **Performance**: Copy project to WSL native filesystem (`~/risk-agent-core`) for faster builds.
- **VS Code**: Install the "WSL" extension for seamless editing.

### Docker Setup
Install Docker Desktop from https://www.docker.com/products/docker-desktop/
```bash
docker --version
docker ps
```

## AWS Configuration
```bash
aws configure --profile <your-aws-profile>
aws sts get-caller-identity --profile <your-aws-profile>
```

## Amazon Bedrock Model Access
The following models must be accessible in your account before deployment:
- **Anthropic Claude Sonnet 4** (`claude-sonnet-4-20250514-v1:0`) — used by all agents
- **Amazon Titan Text Embeddings V2** (`titan-embed-text-v2:0`) — used by Knowledge Base

For Anthropic models, first-time users may need to submit use case details in the Amazon Bedrock console before models can be invoked.

# 2. Setup

## 2.1 Clone and Install Dependencies

```bash
git clone https://github.com/aws-samples/sample-agentic-risk-assessor.git
cd sample-agentic-risk-assessor
cd frontend && npm install && cd ..
```

## 2.2 Manual Terraform Configuration

### Edit bootstrap `terraform.tfvars`

Create `infra/bootstrap/terraform.tfvars` using `terraform.tfvars.example` as a template:

```hcl
aws_account_id = "<your-aws-account-id>"
aws_profile    = "<your-aws-profile>"
region         = "us-east-1"
project_name   = "risk-agent"

terraform_state_bucket = "risk-agent-terraform-state-<your-aws-account-id>"
terraform_locks_table  = "risk-agent-terraform-locks-<your-aws-account-id>"
```

### Edit environment-specific `terraform.tfvars`

Create `infra/environments/staging/terraform.tfvars` using `terraform.tfvars.example` as a template:

```hcl
# Environment Configuration
aws_account_id = "<your-aws-account-id>"
aws_profile    = "<your-aws-profile>"
region         = "us-east-1"
project_name   = "risk-agent"
environment    = "staging"

# Terraform state backend:
terraform_state_bucket = "risk-agent-terraform-state-<your-aws-account-id>"
terraform_locks_table  = "risk-agent-terraform-locks-<your-aws-account-id>"

# Cognito Configuration:
cognito_callback_urls = [
  "http://localhost:3000/auth/callback"  # Add production URLs after deployment
]
cognito_logout_urls = [
  "http://localhost:3000/"
]

# Bedrock Configuration:
bedrock_account_id  = "<your-aws-account-id>"
bedrock_model_id    = "arn:aws:bedrock:us-east-1:<your-aws-account-id>:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0"
bedrock_role_name   = "risk-agent-bedrock-role"
bedrock_max_tokens  = 40000
bedrock_temperature = 0.0
bedrock_top_p       = 0.1
bedrock_top_k       = 1
bedrock_timeout     = 300

# RAG-specific Bedrock configuration:
rag_bedrock_model_id    = "us.anthropic.claude-sonnet-4-20250514-v1:0"
rag_bedrock_temperature = 0.0
rag_bedrock_top_p       = 0.1
rag_bedrock_top_k       = 1

# Federated SSO (Optional - for enterprise OIDC/SAML providers):
# federated_sso_enabled    = true
# federated_sso_client_id  = "<oidc-client-id>"
# federated_sso_issuer     = "https://your-idp.example.com"

# API Gateway (leave empty - auto-populated):
api_gateway_routes = {}
```

### Edit `backend.hcl`

Create `infra/environments/staging/backend.hcl`:

```hcl
bucket         = "risk-agent-terraform-state-<your-aws-account-id>"
key            = "terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "risk-agent-terraform-locks-<your-aws-account-id>"
encrypt        = true
```

## 2.3 Set Environment Variables

```bash
export AWS_PROFILE=<your-aws-profile>
export ENVIRONMENT=staging
```

# 3. 🆕 First-Time Deployment (New AWS Account)

**Prerequisites**: Fresh AWS account with no existing RiskAgent infrastructure.
**⚠️ Critical**: Run steps in exact order.

**Step 1: Bootstrap Terraform Backend** (One-time setup)
```bash
cd infra/bootstrap
terraform init
terraform apply -auto-approve
aws s3 ls | grep terraform-state
cd ../..
```

**Step 2: Build Lambda Packages**
```bash
chmod +x ./infra/scripts/deploy_lambdas_unified.sh
./infra/scripts/deploy_lambdas_unified.sh all build
```

**Step 3: Deploy Infrastructure**
```bash
cd infra/environments/staging
chmod +x ./terraform-wrapper.sh
./terraform-wrapper.sh init
./terraform-wrapper.sh plan
./terraform-wrapper.sh apply
cd ../../..
```

**Step 4: Deploy Lambda Code**
Updates the existing functions with application code (~10 minutes for all functions).
```bash
./infra/scripts/deploy_lambdas_unified.sh all deploy
```

**Step 5: Deploy Agents**
```bash
# Ensure Docker Desktop is running
docker ps

chmod +x ./agents/deploy/deploy_ecs.sh
./agents/deploy/deploy_ecs.sh --clean all
```

**Step 6: Deploy Frontend**
```bash
AWS_PROFILE=<your-aws-profile> ENVIRONMENT=staging ./frontend/deploy_frontend.sh
```

**Step 7: Create First User**
```bash
# Get the Cognito User Pool ID from terraform outputs
cd infra/environments/staging
USER_POOL_ID=$(./terraform-wrapper.sh output -raw cognito_user_pool_id)
cd ../../..

# Create user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username your@email.com \
  --user-attributes Name=email,Value=your@email.com Name=email_verified,Value=true \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username your@email.com \
  --password YourPassword123! \
  --permanent
```

Get your app URL from terraform outputs:
```bash
cd infra/environments/staging && ./terraform-wrapper.sh output | grep cloudfront_domain
```

**Step 8: Populate Knowledge Base (Required for Control Mapping)**

Upload security framework documents to the Knowledge Base S3 bucket, then sync:

```bash
# Get the framework docs bucket name
cd infra/environments/staging
KB_BUCKET=$(./terraform-wrapper.sh output -raw knowledge_base_bucket_name)
cd ../../..

# Upload framework documents (source these from official publications)
# Required folder structure:
#   nist-800-53/    - NIST SP 800-53 Rev 5 PDF
#   pci-dss/        - PCI-DSS v4.0 PDF
#   cps234/         - APRA CPS 234 PDF
#   cri/            - CRI Profile documents (TXT/PDF)
#   cis-controls/   - CIS Controls v8 PDF

# Example: upload your framework documents
aws s3 cp /path/to/your/framework-docs/ s3://$KB_BUCKET/ --recursive

# Sync the Knowledge Base to index the documents
KB_ID=$(./infra/environments/staging/terraform-wrapper.sh output -raw knowledge_base_id)
DS_ID=$(./infra/environments/staging/terraform-wrapper.sh output -raw knowledge_base_data_source_id)
aws bedrock-agent start-ingestion-job --knowledge-base-id $KB_ID --data-source-id $DS_ID --region us-east-1

# Check sync status (wait for COMPLETE)
aws bedrock-agent list-ingestion-jobs --knowledge-base-id $KB_ID --data-source-id $DS_ID --region us-east-1 --query 'ingestionJobSummaries[0].{Status:status,Docs:statistics.numberOfDocumentsScanned}'
```

The ingestion job takes 2-5 minutes depending on document volume. Wait for status `COMPLETE` before using control mapping features.

# 4. 🔄 Code Updates (Existing Environment)

## Lambda Code Updates Only
```bash
# All lambdas:
./infra/scripts/deploy_lambdas_unified.sh all both

# Single lambda:
./infra/scripts/deploy_lambdas_unified.sh <function_name> deploy
```

## Upload System Prompts (if changed)
```bash
./infra/scripts/deploy_lambdas_unified.sh prompts deploy
```

## Agent Code Updates Only
```bash
# All agents:
./agents/deploy/deploy_ecs.sh --clean all

# Single agent:
./agents/deploy/deploy_ecs.sh --clean risk_assessment
```

## Frontend Updates Only
```bash
AWS_PROFILE=<your-aws-profile> ENVIRONMENT=staging ./frontend/deploy_frontend.sh
```

## Infrastructure Changes
```bash
cd infra/environments/staging
./terraform-wrapper.sh apply
```

# 5. Local Development

### Frontend Local Development

**Step 1: Setup Local Environment**
```bash
cd frontend
AWS_PROFILE=<your-aws-profile> ENVIRONMENT=staging ./setup-local-env.sh
```
This generates `.env.local` from terraform outputs — never hardcode values.

**Step 2: Start Development Server**
```bash
npm install  # if not done already
npm run dev
```

**Step 3: Create User Account**
```bash
# Option 1: Navigate to http://localhost:3000/signup

# Option 2: Create via CLI (get user-pool-id from terraform output)
aws cognito-idp admin-create-user \
  --user-pool-id <user-pool-id-from-terraform-output> \
  --username testuser@example.com \
  --user-attributes Name=email,Value=testuser@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id <user-pool-id-from-terraform-output> \
  --username testuser@example.com \
  --password YourPassword123! \
  --permanent
```

**⚠️ Important**: Never hardcode values in `.env.local`. Always use the setup script to pull from terraform outputs.

# 6. Troubleshooting

**First-Time Deployment Issues**:
```bash
# 1. Check AWS credentials
aws sts get-caller-identity --profile <your-aws-profile>

# 2. Run bootstrap first if terraform init fails
cd infra/bootstrap && terraform init && terraform apply -auto-approve && cd ../..

# 3. Re-init main deployment
cd infra/environments/staging && ./terraform-wrapper.sh init
```

**State Lock Errors**: Run bootstrap process first to create backend resources.

**Docker Daemon Not Running**:
```bash
open -a Docker  # macOS
# Wait for Docker to start, then verify:
docker ps
```

**SSL Errors**: Always use wrapper scripts (`terraform-wrapper.sh`, not `terraform` directly).

**Agent Deployment Fails**: Ensure Docker Desktop is running and `AWS_PROFILE` is set.

**Check Deployment Status**:
```bash
cd infra/environments/staging
./terraform-wrapper.sh output

# Check Lambda functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `risk-agent`)].FunctionName'

# Check ECS services
aws ecs list-services --cluster risk-agent-agents
```

**Rollback**:
```bash
# Infrastructure
cd infra/environments/staging
git checkout <previous-commit>
./terraform-wrapper.sh apply

# Agents
IMAGE_TAG=<previous-tag> ./agents/deploy/deploy_ecs.sh all
```

**Missing System Prompts (Agent Startup)**:
```bash
# Upload system prompts
./infra/scripts/deploy_lambdas_unified.sh prompts deploy

# Verify
aws s3 ls "s3://risk-agent-app-data-<bucket-suffix>/system_prompts/"
# Should show: MappingPrompts.json, ControlMappingPrompt.json, FrameworkConfig.json
```

**Word Document Processing Issues**:
```bash
# Rebuild pandoc layer if word uploads fail
./infra/scripts/deploy_lambdas_unified.sh pandoc build
./infra/scripts/deploy_lambdas_unified.sh pandoc deploy
cd infra/environments/staging && ./terraform-wrapper.sh apply
```
