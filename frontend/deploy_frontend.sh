#!/usr/bin/env bash

# Frontend deployment script
# Usage: AWS_PROFILE=$AWS_PROFILE ENVIRONMENT=staging ./deploy_frontend.sh
set -e

if [ -z "$AWS_PROFILE" ]; then
    echo "❌ AWS_PROFILE environment variable is required"
    echo "Usage: AWS_PROFILE=$AWS_PROFILE ENVIRONMENT=staging $0"
    exit 1
fi

if [ -z "$ENVIRONMENT" ]; then
    echo "❌ ENVIRONMENT environment variable is required"
    echo "Usage: AWS_PROFILE=$AWS_PROFILE ENVIRONMENT=staging $0"
    exit 1
fi

echo "🚀 Building and deploying frontend"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/risk-agent-frontend"

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

echo "🔨 Building frontend..."
cd frontend

# Get values from terraform outputs
cd ../infra/environments/$ENVIRONMENT
TF_OUTPUT=$(bash terraform-wrapper.sh output)
API_URL=$(echo "$TF_OUTPUT" | grep 'api_gateway_endpoint' | cut -d'=' -f2 | tr -d ' "')
USER_POOL_ID=$(echo "$TF_OUTPUT" | grep 'cognito_user_pool_id' | cut -d'=' -f2 | tr -d ' "')
CLIENT_ID=$(echo "$TF_OUTPUT" | grep 'cognito_client_id' | cut -d'=' -f2 | tr -d ' "')
CLOUDFRONT_DOMAIN=$(echo "$TF_OUTPUT" | grep 'cloudfront_domain_name' | cut -d'=' -f2 | tr -d ' "')
AGENTS_URL="$CLOUDFRONT_DOMAIN"
FRONTEND_CLUSTER=$(echo "$TF_OUTPUT" | grep 'frontend_cluster_id' | cut -d'=' -f2 | tr -d ' "' | cut -d'/' -f2)
cd ../../../frontend

echo "Using API_URL: $API_URL"
echo "Using USER_POOL_ID: $USER_POOL_ID"
echo "Using CLIENT_ID: $CLIENT_ID"
echo "Using AGENTS_URL: $AGENTS_URL"
echo "Using FRONTEND_CLUSTER: $FRONTEND_CLUSTER"

# Federated SSO configuration
COGNITO_DOMAIN=$(echo "$TF_OUTPUT" | grep 'cognito_domain_url' | cut -d'=' -f2 | tr -d ' "' | sed 's|https://||')
FEDERATED_SSO_ENABLED=$(echo "$TF_OUTPUT" | grep 'federated_sso_enabled' | cut -d'=' -f2 | tr -d ' "')
FEDERATED_SSO_ENABLED=${FEDERATED_SSO_ENABLED:-false}
echo "Using FEDERATED_SSO_ENABLED: $FEDERATED_SSO_ENABLED"
echo "Using COGNITO_DOMAIN: $COGNITO_DOMAIN"

docker build --platform linux/amd64 -t risk-agent-frontend \
  --build-arg NEXT_PUBLIC_API_URL="$API_URL" \
  --build-arg NEXT_PUBLIC_COGNITO_USER_POOL_ID="$USER_POOL_ID" \
  --build-arg NEXT_PUBLIC_COGNITO_CLIENT_ID="$CLIENT_ID" \
  --build-arg NEXT_PUBLIC_AGENTS_URL="$AGENTS_URL" \
  --build-arg NEXT_PUBLIC_FEDERATED_SSO_ENABLED="$FEDERATED_SSO_ENABLED" \
  --build-arg NEXT_PUBLIC_COGNITO_DOMAIN="$COGNITO_DOMAIN" \
  .

echo "📤 Tagging and pushing to ECR..."
docker tag risk-agent-frontend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

echo "✅ Frontend built and pushed"

echo "🔄 Updating ECS service..."
aws ecs update-service \
    --cluster $FRONTEND_CLUSTER \
    --service risk-agent-frontend \
    --force-new-deployment > /dev/null

echo "🎉 Frontend deployment triggered! ECS will roll out the new task automatically."
