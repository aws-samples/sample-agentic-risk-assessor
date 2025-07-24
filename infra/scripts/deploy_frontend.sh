#!/usr/bin/env bash

# Deploy Frontend to ECS with Security Features
# Usage: ./deploy_frontend.sh <environment> <aws_profile> <aws_region>

set -e

# Check required parameters
if [ $# -lt 3 ]; then
    echo "Usage: $0 <environment> <aws_profile> <aws_region>"
    echo "Example: $0 staging <YOUR_AWS_PROFILE> us-east-1"
    exit 1
fi

ENVIRONMENT=$1
AWS_PROFILE=$2
AWS_REGION=$3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Frontend Deployment${NC}"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/frontend/package.json" ]; then
    echo -e "${RED}❌ Frontend directory not found${NC}"
    exit 1
fi

# Get configuration from Terraform outputs
echo -e "${YELLOW}📋 Getting configuration from Terraform ($ENVIRONMENT)...${NC}"
cd "$PROJECT_ROOT/infra/environments/$ENVIRONMENT"

# Check if environment directory exists
if [ ! -d "$PROJECT_ROOT/infra/environments/$ENVIRONMENT" ]; then
    echo -e "${RED}❌ Environment '$ENVIRONMENT' not found${NC}"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile $AWS_PROFILE)

# Get values from Terraform outputs
echo -e "${YELLOW}Getting ECR repository URL...${NC}"
ECR_URI=$(AWS_PROFILE=$AWS_PROFILE ./terraform-wrapper.sh output -raw frontend_ecr_repository_url 2>/dev/null | tail -1)
echo -e "${YELLOW}Getting cluster ARN...${NC}"
CLUSTER_ARN=$(AWS_PROFILE=$AWS_PROFILE ./terraform-wrapper.sh output -raw frontend_cluster_id 2>/dev/null | tail -1)
CLUSTER_NAME=$(echo $CLUSTER_ARN | cut -d'/' -f2)
SERVICE_NAME="risk-agent-frontend"  # Service name from frontend module
ECR_REPO_NAME="risk-agent-frontend"

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  Region: $AWS_REGION"
echo "  ECR Repository: $ECR_URI"
echo "  Cluster: $CLUSTER_NAME"
echo "  Service: $SERVICE_NAME"

# Validate required values
if [ -z "$ECR_URI" ] || [ -z "$CLUSTER_NAME" ]; then
    echo -e "${RED}❌ Failed to get required values from Terraform${NC}"
    exit 1
fi

# Login to ECR
echo -e "${YELLOW}🔐 Logging into ECR...${NC}"
ECR_REGISTRY=$(echo $ECR_URI | cut -d'/' -f1)
aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | docker login --username AWS --password-stdin $ECR_REGISTRY

# Get environment variables from Terraform
echo -e "${YELLOW}🔧 Getting environment variables...${NC}"
COGNITO_USER_POOL_ID=$(AWS_PROFILE=$AWS_PROFILE ./terraform-wrapper.sh output -raw cognito_user_pool_id 2>/dev/null | tail -1)
COGNITO_CLIENT_ID=$(AWS_PROFILE=$AWS_PROFILE ./terraform-wrapper.sh output -raw cognito_client_id 2>/dev/null | tail -1)
AGENTS_ALB_DNS=$(AWS_PROFILE=$AWS_PROFILE ./terraform-wrapper.sh output -raw agents_alb_dns_name 2>/dev/null | tail -1)
CLOUDFRONT_DOMAIN=$(AWS_PROFILE=$AWS_PROFILE ./terraform-wrapper.sh output -raw cloudfront_domain_name 2>/dev/null | tail -1)

API_URL="https://${CLOUDFRONT_DOMAIN}"
AGENTS_URL="http://${AGENTS_ALB_DNS}"

echo -e "${YELLOW}Environment variables:${NC}"
echo "  API_URL: $API_URL"
echo "  AGENTS_URL: $AGENTS_URL"
echo "  COGNITO_USER_POOL_ID: $COGNITO_USER_POOL_ID"
echo "  COGNITO_CLIENT_ID: $COGNITO_CLIENT_ID"

# Build Docker image
echo -e "${YELLOW}🏗️  Building Docker image...${NC}"
cd "$PROJECT_ROOT/frontend"
docker build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL="$API_URL" \
  --build-arg NEXT_PUBLIC_AGENTS_URL="$AGENTS_URL" \
  --build-arg NEXT_PUBLIC_COGNITO_USER_POOL_ID="$COGNITO_USER_POOL_ID" \
  --build-arg NEXT_PUBLIC_COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
  -t $ECR_REPO_NAME .

# Tag image
echo -e "${YELLOW}🏷️  Tagging image...${NC}"
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest

# Push to ECR
echo -e "${YELLOW}📤 Pushing to ECR...${NC}"
docker push $ECR_URI:latest

# Update ECS service
echo -e "${YELLOW}🔄 Updating ECS service...${NC}"
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --force-new-deployment \
    --region $AWS_REGION \
    --profile $AWS_PROFILE

# Wait for deployment to complete
echo -e "${YELLOW}⏳ Waiting for deployment to complete...${NC}"
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE

# Get service URL (no ALB configured yet)
echo -e "${YELLOW}📋 Getting service details...${NC}"
SERVICE_INFO=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE)

echo -e "${GREEN}✅ Frontend deployment completed successfully!${NC}"
echo -e "${YELLOW}📋 Service Details:${NC}"
echo "  Cluster: $CLUSTER_NAME"
echo "  Service: $SERVICE_NAME"
echo "  ECR Repository: $ECR_URI"
echo -e "${YELLOW}🔍 Check ECS console for service status and public IP${NC}"