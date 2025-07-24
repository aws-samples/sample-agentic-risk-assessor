#!/usr/bin/env bash

# Deploy Agents and API Infrastructure
# This script deploys the complete RiskAgent.Agentic system
set -e

PROJECT_NAME="risk-agent"
AWS_REGION="us-east-1"
AWS_PROFILE="risk-agent"
TERRAFORM_DIR="infra/terraform"

echo "🚀 Starting RiskAgent.Agentic Deployment"
echo "========================================"

# Function to check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI not found. Please install AWS CLI."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo "❌ Terraform not found. Please install Terraform."
        exit 1
    fi
    
    # Check container runtime
    if command -v finch &> /dev/null; then
        CONTAINER_CMD="finch"
        echo "📦 Using Finch"
    elif command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
        echo "📦 Using Docker"
    else
        echo "❌ Neither Finch nor Docker found. Please install one of them."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity --profile $AWS_PROFILE &> /dev/null; then
        echo "❌ AWS credentials not configured for profile: $AWS_PROFILE"
        echo "Please run: aws configure --profile $AWS_PROFILE"
        exit 1
    fi
    
    echo "✅ Prerequisites check passed"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    echo ""
    echo "🏗️  Deploying Infrastructure with Terraform"
    echo "============================================"
    
    cd $TERRAFORM_DIR
    
    # Initialize Terraform
    echo "📦 Initializing Terraform..."
    AWS_PROFILE=$AWS_PROFILE terraform init
    
    # Plan deployment
    echo "📋 Planning deployment..."
    AWS_PROFILE=$AWS_PROFILE terraform plan -out=tfplan
    
    # Apply deployment
    echo "🚀 Applying infrastructure changes..."
    AWS_PROFILE=$AWS_PROFILE terraform apply tfplan
    
    # Clean up plan file
    rm -f tfplan
    
    echo "✅ Infrastructure deployment completed"
    cd - > /dev/null
}

# Function to build and deploy agents
deploy_agents() {
    echo ""
    echo "🤖 Building and Deploying Agents"
    echo "================================="
    
    # Get AWS account and ECR registry
    ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
    ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    CLUSTER_NAME="$PROJECT_NAME-agents-cluster"
    
    # All agents to deploy
    AGENTS=("orchestrator" "architect" "risk_framework" "security_architect" "risk_assessment")
    
    # Login to ECR
    echo "🔐 Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | $CONTAINER_CMD login --username AWS --password-stdin $ECR_REGISTRY
    
    # Build and push each agent
    for agent in "${AGENTS[@]}"; do
        echo "🔨 Building and pushing $agent..."
        
        # Upload system prompts to S3 if they exist
        upload_agent_prompts $agent
        
        # Build image
        $CONTAINER_CMD build --platform linux/amd64 -f agents/deploy/Dockerfile.$agent -t $PROJECT_NAME-$agent:latest . -q
        
        # Tag for ECR
        $CONTAINER_CMD tag $PROJECT_NAME-$agent:latest $ECR_REGISTRY/$PROJECT_NAME-$agent:latest
        
        # Create ECR repo if needed
        aws ecr describe-repositories --repository-names $PROJECT_NAME-$agent --region $AWS_REGION --profile $AWS_PROFILE >/dev/null 2>&1 || \
        aws ecr create-repository --repository-name $PROJECT_NAME-$agent --region $AWS_REGION --profile $AWS_PROFILE >/dev/null
        
        # Push to ECR
        $CONTAINER_CMD push $ECR_REGISTRY/$PROJECT_NAME-$agent:latest -q
        echo "✅ $agent built and pushed"
    done
    
    # Update ECS services
    update_ecs_services
}

# Function to upload agent prompts and templates
upload_agent_prompts() {
    local agent=$1
    
    # Upload system prompt if it exists
    if [ -f "agents/$agent/prompts/system_prompt.md" ]; then
        echo "📝 Uploading system prompt for $agent..."
        aws s3 cp "agents/$agent/prompts/system_prompt.md" "s3://risk-agent-app-data/system_prompts/${agent}_system_prompt.md" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload system prompt for $agent"
    # Upload security architect specific prompts
    elif [ "$agent" = "security_architect" ]; then
        if [ -f "agents/$agent/prompts/generate_security_questions.txt" ]; then
            echo "📝 Uploading security questions prompt for $agent..."
            aws s3 cp "agents/$agent/prompts/generate_security_questions.txt" "s3://risk-agent-app-data/system_prompts/security_architect/generate_security_questions.txt" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload security questions prompt for $agent"
        fi
        if [ -f "agents/$agent/prompts/security_questions_evaluation.txt" ]; then
            echo "📝 Uploading security evaluation prompt for $agent..."
            aws s3 cp "agents/$agent/prompts/security_questions_evaluation.txt" "s3://risk-agent-app-data/system_prompts/security_architect/security_questions_evaluation.txt" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload security evaluation prompt for $agent"
        fi
        if [ -f "agents/$agent/prompts/security_assessment.txt" ]; then
            echo "📝 Uploading security assessment prompt for $agent..."
            aws s3 cp "agents/$agent/prompts/security_assessment.txt" "s3://risk-agent-app-data/system_prompts/security_architect/security_assessment.txt" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload security assessment prompt for $agent"
        fi
    elif [ -f "agents/$agent/system_prompt.md" ]; then
        echo "📝 Uploading system prompt for $agent..."
        aws s3 cp "agents/$agent/system_prompt.md" "s3://risk-agent-app-data/system_prompts/${agent}_system_prompt.md" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload system prompt for $agent"
    fi
    
    # Upload specific prompts for architect
    if [ "$agent" = "architect" ] && [ -f "agents/$agent/prompts/generate_clarification_questions_lambda.txt" ]; then
        echo "📝 Uploading clarification questions prompt for $agent..."
        aws s3 cp "agents/$agent/prompts/generate_clarification_questions_lambda.txt" "s3://risk-agent-app-data/system_prompts/architect/generate_clarification_questions_lambda.txt" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload clarification questions prompt for $agent"
    fi
    
    # Upload risk assessment templates
    if [ "$agent" = "risk_assessment" ]; then
        if [ -f "agents/$agent/templates/fsi_assessment_template.json" ]; then
            echo "📝 Uploading FSI assessment template for $agent..."
            aws s3 cp "agents/$agent/templates/fsi_assessment_template.json" "s3://risk-agent-app-data/risk_assessment/templates/fsi_assessment_template.json" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload FSI template for $agent"
        fi
        if [ -f "agents/$agent/templates/agent_prompts.json" ]; then
            echo "📝 Uploading agent prompts for $agent..."
            aws s3 cp "agents/$agent/templates/agent_prompts.json" "s3://risk-agent-app-data/risk_assessment/templates/agent_prompts.json" --profile $AWS_PROFILE >/dev/null 2>&1 || echo "⚠️ Failed to upload agent prompts for $agent"
        fi
    fi
}

# Function to update ECS services
update_ecs_services() {
    echo "🔄 Updating ECS services..."
    
    CLUSTER_NAME="$PROJECT_NAME-agents-cluster"
    AGENTS=("orchestrator" "architect" "risk_framework" "security_architect" "risk_assessment")
    
    # Map agent names to service names
    get_service_name() {
        case $1 in
            "risk_framework") echo "risk-agent-risk-framework" ;;
            "security_architect") echo "risk-agent-security-architect" ;;
            "risk_assessment") echo "risk-agent-risk-assessment" ;;
            *) echo "risk-agent-$1" ;;
        esac
    }
    
    # Update each service
    for agent in "${AGENTS[@]}"; do
        SERVICE_NAME=$(get_service_name $agent)
        
        echo "📦 Updating service: $SERVICE_NAME"
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $SERVICE_NAME \
            --force-new-deployment \
            --deployment-configuration maximumPercent=200,minimumHealthyPercent=0 \
            --profile $AWS_PROFILE \
            --region $AWS_REGION >/dev/null 2>&1
        
        echo "✓ $agent deployment triggered"
    done
}

# Function to verify deployment
verify_deployment() {
    echo ""
    echo "🔍 Verifying Deployment"
    echo "======================="
    
    # Check API Gateway
    echo "🌐 Checking API Gateway..."
    API_URL=$(aws apigatewayv2 get-apis --profile $AWS_PROFILE --region $AWS_REGION --query 'Items[?Name==`risk-agent-api`].ApiEndpoint' --output text 2>/dev/null || echo "")
    if [ ! -z "$API_URL" ]; then
        echo "✅ API Gateway deployed: $API_URL"
    else
        echo "❌ API Gateway not found"
    fi
    
    # Check ALB
    echo "🔗 Checking Application Load Balancer..."
    ALB_DNS=$(aws elbv2 describe-load-balancers --profile $AWS_PROFILE --region $AWS_REGION --query 'LoadBalancers[?LoadBalancerName==`risk-agent-agents-alb`].DNSName' --output text 2>/dev/null || echo "")
    if [ ! -z "$ALB_DNS" ]; then
        echo "✅ ALB deployed: $ALB_DNS"
    else
        echo "❌ ALB not found"
    fi
    
    # Check ECS services
    echo "🤖 Checking ECS services..."
    CLUSTER_NAME="$PROJECT_NAME-agents-cluster"
    AGENTS=("orchestrator" "architect" "risk_framework" "security_architect" "risk_assessment")
    FAILED=()
    
    get_service_name() {
        case $1 in
            "risk_framework") echo "risk-agent-risk-framework" ;;
            "security_architect") echo "risk-agent-security-architect" ;;
            "risk_assessment") echo "risk-agent-risk-assessment" ;;
            *) echo "risk-agent-$1" ;;
        esac
    }
    
    for agent in "${AGENTS[@]}"; do
        SERVICE_NAME=$(get_service_name $agent)
        
        # Check service status
        SERVICE_INFO=$(aws ecs describe-services \
            --cluster $CLUSTER_NAME \
            --services $SERVICE_NAME \
            --profile $AWS_PROFILE \
            --region $AWS_REGION \
            --query 'services[0].{runningCount:runningCount,desiredCount:desiredCount}' \
            2>/dev/null || echo '{"runningCount":0,"desiredCount":1}')
        
        RUNNING=$(echo $SERVICE_INFO | jq -r '.runningCount // 0')
        DESIRED=$(echo $SERVICE_INFO | jq -r '.desiredCount // 1')
        
        if [ "$RUNNING" -ge "1" ]; then
            echo "✅ $agent: $RUNNING/$DESIRED tasks running"
        else
            echo "❌ $agent: $RUNNING/$DESIRED tasks running"
            FAILED+=($agent)
        fi
    done
    
    # Summary
    echo ""
    if [ ${#FAILED[@]} -eq 0 ]; then
        echo "🎉 Deployment verification successful!"
        echo ""
        echo "📋 Deployment Summary:"
        echo "====================="
        [ ! -z "$API_URL" ] && echo "🌐 API Gateway: $API_URL/prod"
        [ ! -z "$ALB_DNS" ] && echo "🔗 Agents ALB: http://$ALB_DNS"
        echo "🤖 All 5 agents deployed and running"
        echo ""
        echo "🔗 Quick Links:"
        echo "- Orchestrator: http://$ALB_DNS/orchestrator"
        echo "- Architect: http://$ALB_DNS/architect"
        echo "- Risk Framework: http://$ALB_DNS/risk-framework"
        echo "- Security Architect: http://$ALB_DNS/security-architect"
        echo "- Risk Assessment: http://$ALB_DNS/risk-assessment"
    else
        echo "❌ Some services failed: ${FAILED[*]}"
        echo "Check CloudWatch logs for details"
        exit 1
    fi
}

# Main execution
main() {
    check_prerequisites
    deploy_infrastructure
    deploy_agents
    verify_deployment
}

# Parse command line arguments
case "${1:-all}" in
    "infra"|"infrastructure")
        check_prerequisites
        deploy_infrastructure
        ;;
    "agents")
        check_prerequisites
        deploy_agents
        ;;
    "verify")
        verify_deployment
        ;;
    "all"|*)
        main
        ;;
esac