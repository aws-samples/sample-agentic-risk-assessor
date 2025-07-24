#!/usr/bin/env bash

# Setup local environment variables from terraform outputs
# Usage: AWS_PROFILE=$AWS_PROFILE ENVIRONMENT=staging ./setup-local-env.sh

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

echo "🔧 Setting up local environment from terraform outputs..."

# Get terraform outputs
cd ../infra/environments/$ENVIRONMENT
TF_OUTPUT=$(bash terraform-wrapper.sh output $AWS_PROFILE)

# Extract values
API_URL=$(echo "$TF_OUTPUT" | grep 'api_gateway_endpoint' | cut -d'=' -f2 | tr -d ' "')
USER_POOL_ID=$(echo "$TF_OUTPUT" | grep 'cognito_user_pool_id' | cut -d'=' -f2 | tr -d ' "')
CLIENT_ID=$(echo "$TF_OUTPUT" | grep 'cognito_client_id' | cut -d'=' -f2 | tr -d ' "')
CLOUDFRONT_DOMAIN=$(echo "$TF_OUTPUT" | grep 'cloudfront_domain_name' | cut -d'=' -f2 | tr -d ' "')
AGENTS_ALB=$(echo "$TF_OUTPUT" | grep 'agents_alb_dns_name' | cut -d'=' -f2 | tr -d ' "')

cd ../../../frontend

# Create .env.local with dynamic values
cat > .env.local << EOF
# AWS Cognito Configuration
NEXT_PUBLIC_COGNITO_USER_POOL_ID=$USER_POOL_ID
NEXT_PUBLIC_COGNITO_CLIENT_ID=$CLIENT_ID

# API Gateway URL
NEXT_PUBLIC_API_URL=$API_URL

# CloudFront Distribution URL
NEXT_PUBLIC_CLOUDFRONT_URL=https://$CLOUDFRONT_DOMAIN

# Agents ALB URL (for WebSocket connections - CloudFront doesn't support WebSocket)
NEXT_PUBLIC_AGENTS_URL=$AGENTS_ALB
EOF

echo "✅ Local environment configured:"
echo "   API_URL: $API_URL"
echo "   USER_POOL_ID: $USER_POOL_ID"
echo "   CLIENT_ID: $CLIENT_ID"
echo "   CLOUDFRONT_URL: https://$CLOUDFRONT_DOMAIN"
echo "   AGENTS_URL: $AGENTS_ALB"