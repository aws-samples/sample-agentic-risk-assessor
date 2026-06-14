#!/usr/bin/env bash

# Fast Build & Deploy Script
set -e

PROJECT_NAME="risk-agent"
AWS_REGION="us-east-1"

CLUSTER_NAME="$PROJECT_NAME-agents"

# All available agents
ALL_AGENTS=("architect" "security_architect" "risk_assessment" "auditor" "organization_profile")

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS] <agent_name|all>"
    echo ""
    echo "Options:"
    echo "  --help, -h                 Show this help message"
    echo "  --clean, --no-cache        Force clean build without Docker cache"
    echo "  --force-clean              Clean all Docker cache and force rebuild"
    echo ""
    echo "Available agents: ${ALL_AGENTS[*]}"
    echo ""
    echo "Examples:"
    echo "  $0 risk_assessment                    # Normal deployment"
    echo "  $0 --clean risk_assessment           # Clean build deployment"
    echo "  $0 --force-clean all                 # Clean build all agents"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_PROFILE                Required AWS profile for deployment"
}

# Show help if no arguments provided
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# Check if AWS profile is provided
if [ -z "$AWS_PROFILE" ]; then
    echo "❌ AWS_PROFILE environment variable is required"
    echo ""
    show_help
    exit 1
fi

# Initialize options
CLEAN_BUILD=false
NO_CACHE=false

# Parse command line arguments
AGENTS_TO_DEPLOY=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --clean|--no-cache)
            CLEAN_BUILD=true
            NO_CACHE=true
            echo "🔄 Clean build enabled"
            shift
            ;;
        --force-clean)
            CLEAN_BUILD=true
            NO_CACHE=true
            echo "🧹 Force clean build enabled - will remove all Docker cache"
            shift
            ;;
        all)
            AGENTS_TO_DEPLOY=("${ALL_AGENTS[@]}")
            echo "🚀 Building and deploying ALL agents"
            shift
            ;;
        architect|security_architect|risk_assessment|auditor|organization_profile)
            AGENTS_TO_DEPLOY+=("$1")
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
done

# Check if agents were specified
if [ ${#AGENTS_TO_DEPLOY[@]} -eq 0 ]; then
    echo "❌ No agents specified for deployment"
    echo ""
    show_help
    exit 1
fi

echo "🚀 Building and deploying: ${AGENTS_TO_DEPLOY[*]}"

# Detect container runtime
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

# Get AWS account and ECR registry
ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Get S3 bucket name from Terraform output
# Get S3 bucket name from Terraform output
if [ -z "$APP_DATA_BUCKET" ]; then
    APP_DATA_BUCKET=$(cd infra/environments/staging && AWS_PROFILE=$AWS_PROFILE bash terraform-wrapper.sh output 2>/dev/null | grep 'app_data' | cut -d'=' -f2 | tr -d ' "')
fi

# Validate that APP_DATA_BUCKET was successfully retrieved
if [ -z "$APP_DATA_BUCKET" ]; then
    echo "❌ Failed to retrieve APP_DATA_BUCKET from Terraform output"
    echo "   This could be due to:"
    echo "   - Terraform state not found in infra/environments/staging"
    echo "   - terraform-wrapper.sh script not found or failed"
    echo "   - 'app_data' output not defined in Terraform configuration"
    echo "   - AWS profile '$AWS_PROFILE' lacks permissions"
    echo ""
    echo "   Please ensure:"
    echo "   1. Terraform has been applied in infra/environments/staging"
    echo "   2. The 'app_data' output is defined in your Terraform configuration"
    echo "   3. Your AWS profile has access to the Terraform state"
    exit 1
fi
echo "📦 Using S3 bucket: $APP_DATA_BUCKET"

# Cache management functions
clean_docker_cache() {
    echo "🧹 Cleaning Docker cache..."
    if [ "$CLEAN_BUILD" = "true" ]; then
        $CONTAINER_CMD system prune -f
        echo "✅ Docker cache cleaned"
    fi
}

get_build_args() {
    local agent=$1
    
    if [ "$NO_CACHE" = "true" ]; then
        echo "--no-cache"
    else
        # Use build timestamp to invalidate cache when needed
        local build_timestamp=$(date +%s)
        local git_hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        echo "--build-arg BUILD_TIMESTAMP=$build_timestamp --build-arg GIT_HASH=$git_hash"
    fi
}

# Deployment verification functions
verify_code_in_container() {
    local agent=$1
    local image_name="$PROJECT_NAME-$agent:latest"
    
    echo "🔍 Verifying code in container for $agent..."
    
    case $agent in
        "risk_assessment")
            # Verify our structured tool is in the container
            local verification_pattern="perform_full_risk_assessment"
            local file_path="/app/agents/risk_assessment/agent.py"
            ;;
        "security_architect")
            local verification_pattern="perform_security_assessment"
            local file_path="/app/agents/security_architect/agent.py"
            ;;
        "architect")
            local verification_pattern="get_fsi_review_prompt"
            local file_path="/app/agents/architect/agent.py"
            ;;
        "auditor")
            local verification_pattern="validate_risk_assessment"
            local file_path="/app/agents/auditor/agent.py"
            ;;
        "organization_profile")
            local verification_pattern="create_profile"
            local file_path="/app/agents/organization_profile/agent.py"
            ;;
        *)
            echo "⚠️  No verification pattern defined for $agent"
            return 0
            ;;
    esac
    
    # Check if the expected code is in the container
    if $CONTAINER_CMD run --rm --platform linux/amd64 $image_name grep -q "$verification_pattern" "$file_path" 2>/dev/null; then
        echo "✅ Code verification passed for $agent"
        return 0
    else
        echo "❌ Code verification failed for $agent - expected pattern '$verification_pattern' not found"
        return 1
    fi
}

verify_deployment_success() {
    local agent=$1
    local service_name=$(get_service_name $agent)
    local max_attempts=12
    local attempt=1
    
    echo "🔍 Verifying deployment success for $agent..."
    
    while [ $attempt -le $max_attempts ]; do
        # Get current task ARN
        local task_arn=$(aws ecs list-tasks \
            --cluster $CLUSTER_NAME \
            --service-name $service_name \
            --profile $AWS_PROFILE \
            --region $AWS_REGION \
            --query 'taskArns[0]' \
            --output text 2>/dev/null)
        
        if [ "$task_arn" != "None" ] && [ ! -z "$task_arn" ]; then
            # Get task creation time
            local task_info=$(aws ecs describe-tasks \
                --cluster $CLUSTER_NAME \
                --tasks $task_arn \
                --profile $AWS_PROFILE \
                --region $AWS_REGION \
                --query 'tasks[0].{createdAt:createdAt,lastStatus:lastStatus}' 2>/dev/null)
            
            local status=$(echo $task_info | jq -r '.lastStatus // "UNKNOWN"')
            
            if [ "$status" = "RUNNING" ]; then
                echo "✅ Deployment verification passed for $agent (attempt $attempt/$max_attempts)"
                return 0
            fi
        fi
        
        echo "⏳ Waiting for $agent deployment... (attempt $attempt/$max_attempts, status: $status)"
        sleep 10
        ((attempt++))
    done
    
    echo "❌ Deployment verification failed for $agent after $max_attempts attempts"
    return 1
}


# Step 1: Build and push containers
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | $CONTAINER_CMD login --username AWS --password-stdin $ECR_REGISTRY

# Clean cache if requested
if [ "$CLEAN_BUILD" = "true" ]; then
    clean_docker_cache
fi

for agent in "${AGENTS_TO_DEPLOY[@]}"; do
    echo "🔨 Building $agent..."
    
    # Upload system prompt to S3 if it exists
    if [ "$agent" = "security_architect" ]; then
        if [ -f "agents/security_architect/prompts/system_prompt.xml" ]; then
            echo "📝 Uploading system prompt (XML) for $agent..."
            aws s3 cp "agents/security_architect/prompts/system_prompt.xml" "s3://$APP_DATA_BUCKET/system_prompts/security_architect_system_prompt.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload system prompt for $agent"
        fi
    elif [ "$agent" = "risk_assessment" ]; then
        # Risk assessment uses XML format
        if [ -f "agents/$agent/prompts/system_prompt.xml" ]; then
            echo "📝 Uploading system prompt (XML) for $agent..."
            aws s3 cp "agents/$agent/prompts/system_prompt.xml" "s3://$APP_DATA_BUCKET/system_prompts/${agent}_system_prompt.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload system prompt for $agent"
        fi
    elif [ "$agent" = "architect" ] || [ "$agent" = "auditor" ]; then
        if [ -f "agents/$agent/prompts/system_prompt.xml" ]; then
            echo "📝 Uploading system prompt (XML) for $agent..."
            aws s3 cp "agents/$agent/prompts/system_prompt.xml" "s3://$APP_DATA_BUCKET/system_prompts/${agent}_system_prompt.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload system prompt for $agent"
        fi
    elif [ "$agent" = "organization_profile" ]; then
        # Upload system prompt
        if [ -f "agents/$agent/prompts/system_prompt.xml" ]; then
            echo "📝 Uploading system prompt (XML) for $agent..."
            aws s3 cp "agents/$agent/prompts/system_prompt.xml" "s3://$APP_DATA_BUCKET/system_prompts/${agent}_system_prompt.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload system prompt for $agent"
        fi
        # Upload configuration files
        if [ -d "agents/$agent/config" ]; then
            echo "📦 Uploading configuration files for $agent..."
            # Upload main config
            if [ -f "agents/$agent/config/profile_config.yaml" ]; then
                aws s3 cp "agents/$agent/config/profile_config.yaml" "s3://$APP_DATA_BUCKET/config/organization_profile/profile_config.yaml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload profile_config.yaml"
            fi
            # Upload industry configs
            if [ -d "agents/$agent/config/industries" ]; then
                aws s3 sync "agents/$agent/config/industries/" "s3://$APP_DATA_BUCKET/config/organization_profile/industries/" --profile $AWS_PROFILE || echo "⚠️ Failed to upload industry configs"
            fi
            # Upload region configs
            if [ -d "agents/$agent/config/regions" ]; then
                aws s3 sync "agents/$agent/config/regions/" "s3://$APP_DATA_BUCKET/config/organization_profile/regions/" --profile $AWS_PROFILE || echo "⚠️ Failed to upload region configs"
            fi
            echo "✅ Configuration files uploaded"
        fi
    elif [ -f "agents/$agent/prompts/system_prompt.md" ]; then
        echo "📝 Uploading system prompt for $agent..."
        aws s3 cp "agents/$agent/prompts/system_prompt.md" "s3://$APP_DATA_BUCKET/system_prompts/${agent}_system_prompt.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload system prompt for $agent"
    elif [ -f "agents/$agent/system_prompt.md" ]; then
        echo "📝 Uploading system prompt for $agent..."
        aws s3 cp "agents/$agent/system_prompt.md" "s3://$APP_DATA_BUCKET/system_prompts/${agent}_system_prompt.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload system prompt for $agent"
    fi
    
    # Upload architect specific prompts
    if [ "$agent" = "architect" ]; then
        if [ -f "agents/$agent/prompts/fsi_architecture_review.xml" ]; then
            echo "📝 Uploading FSI architecture review prompt (XML) for $agent..."
            aws s3 cp "agents/$agent/prompts/fsi_architecture_review.xml" "s3://$APP_DATA_BUCKET/system_prompts/architect/fsi_architecture_review.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI architecture review prompt for $agent"
        fi
        if [ -f "agents/$agent/prompts/triage_clarification.md" ]; then
            echo "📝 Uploading triage clarification prompt for $agent..."
            aws s3 cp "agents/$agent/prompts/triage_clarification.md" "s3://$APP_DATA_BUCKET/system_prompts/architect/triage_clarification.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload triage clarification prompt for $agent"
        fi
    fi
    
    # Upload security architect specific prompts
    if [ "$agent" = "security_architect" ]; then
        echo "DEBUG: Processing security_architect prompts..."
        if [ -f "agents/security_architect/prompts/triage_security_assessment.md" ]; then
            echo "📝 Uploading security triage assessment prompt for $agent..."
            aws s3 cp "agents/security_architect/prompts/triage_security_assessment.md" "s3://$APP_DATA_BUCKET/system_prompts/security_architect/triage_security_assessment.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload security triage assessment prompt for $agent"
        fi
        if [ -f "agents/security_architect/prompts/fsi_security_architecture_review.xml" ]; then
            echo "📝 Uploading FSI security architecture review prompt (XML) for $agent..."
            aws s3 cp "agents/security_architect/prompts/fsi_security_architecture_review.xml" "s3://$APP_DATA_BUCKET/system_prompts/security_architect/fsi_security_architecture_review.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI security architecture review prompt for $agent"
        fi

    fi
    
    # Upload risk assessment templates
    if [ "$agent" = "risk_assessment" ]; then
        # Note: fsi_assessment_template.json doesn't exist, skipping
        if [ -f "agents/$agent/prompts/fsi_assessment_prompt.xml" ]; then
            echo "📝 Uploading FSI assessment prompt for $agent..."
            aws s3 cp "agents/$agent/prompts/fsi_assessment_prompt.xml" "s3://$APP_DATA_BUCKET/risk_assessment/prompts/fsi_assessment_prompt.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI assessment prompt for $agent"
        fi
        if [ -f "agents/$agent/templates/FSI_Risk_Framework_Template.md" ]; then
            echo "📝 Uploading FSI Risk Framework Template for $agent..."
            aws s3 cp "agents/$agent/templates/FSI_Risk_Framework_Template.md" "s3://$APP_DATA_BUCKET/risk_assessment/templates/FSI_Risk_Framework_Template.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI Risk Framework Template for $agent"
        fi
        if [ -f "agents/$agent/templates/FSI_Risk_Assessment_Template_Short.md" ]; then
            echo "📝 Uploading FSI Risk Assessment Template Short for $agent..."
            aws s3 cp "agents/$agent/templates/FSI_Risk_Assessment_Template_Short.md" "s3://$APP_DATA_BUCKET/risk_assessment/templates/FSI_Risk_Assessment_Template_Short.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI Risk Assessment Template Short for $agent"
        fi
        if [ -f "agents/$agent/prompts/fsi_assessment_prompt_short.md" ]; then
            echo "📝 Uploading FSI assessment prompt short for $agent..."
            aws s3 cp "agents/$agent/prompts/fsi_assessment_prompt_short.md" "s3://$APP_DATA_BUCKET/risk_assessment/prompts/fsi_assessment_prompt_short.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI assessment prompt short for $agent"
        fi
        if [ -f "agents/$agent/prompts/fsi_assessment_prompt_demo.xml" ]; then
            echo "📝 Uploading FSI assessment prompt demo for $agent..."
            aws s3 cp "agents/$agent/prompts/fsi_assessment_prompt_demo.xml" "s3://$APP_DATA_BUCKET/risk_assessment/prompts/fsi_assessment_prompt_demo.xml" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI assessment prompt demo for $agent"
        fi
        if [ -f "agents/$agent/templates/FSI_Risk_Assessment_Template_Demo.md" ]; then
            echo "📝 Uploading FSI Risk Assessment Template Demo for $agent..."
            aws s3 cp "agents/$agent/templates/FSI_Risk_Assessment_Template_Demo.md" "s3://$APP_DATA_BUCKET/risk_assessment/templates/FSI_Risk_Assessment_Template_Demo.md" --profile $AWS_PROFILE || echo "⚠️ Failed to upload FSI Risk Assessment Template Demo for $agent"
        fi
    fi
    
    # Get build arguments
    BUILD_ARGS=$(get_build_args $agent)

    # Build image with appropriate cache strategy
    echo "🔨 Building $agent with strategy: $([ "$NO_CACHE" = "true" ] && echo "clean build" || echo "cached build")"
    if [ "$NO_CACHE" = "true" ]; then
        echo "🔄 Using --no-cache for clean build"
    else
        echo "📦 Using cache with build args"
    fi

    if [ "$agent" = "risk-assessment" ]; then
        DOCKERFILE="agents/deploy/Dockerfile.risk_assessment"
    elif [ "$agent" = "security_architect" ]; then
        DOCKERFILE="agents/deploy/Dockerfile.security_architect"
    else
        DOCKERFILE="agents/deploy/Dockerfile.$agent"
    fi

    # Execute build with build args
    $CONTAINER_CMD build --platform linux/amd64 $BUILD_ARGS -f $DOCKERFILE -t $PROJECT_NAME-$agent:latest . -q

    if [ $? -ne 0 ]; then
        echo "❌ Build failed for $agent"
        exit 1
    fi

    echo "✅ Build completed for $agent"

    # After successful build, verify the container contains expected code
    if ! verify_code_in_container $agent; then
        echo "❌ Aborting deployment for $agent due to code verification failure"
        exit 1
    fi
    
    # Handle ECR repository naming (underscores vs hyphens)
    if [ "$agent" = "risk_assessment" ]; then
        ECR_REPO_NAME="$PROJECT_NAME-risk_assessment"
    elif [ "$agent" = "security_architect" ]; then
        ECR_REPO_NAME="$PROJECT_NAME-security_architect"
    else
        ECR_REPO_NAME="$PROJECT_NAME-$agent"
    fi
    
    # Tag for ECR
    $CONTAINER_CMD tag $PROJECT_NAME-$agent:latest $ECR_REGISTRY/$ECR_REPO_NAME:latest
    
    # Create ECR repo if needed
    aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION --profile $AWS_PROFILE >/dev/null 2>&1 || \
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION --profile $AWS_PROFILE >/dev/null
    
    # Push to ECR
    $CONTAINER_CMD push $ECR_REGISTRY/$ECR_REPO_NAME:latest -q
    echo "✅ $agent built and pushed"
done

# Map agent names to actual service names
get_service_name() {
    case $1 in
        "security_architect") echo "risk-agent-security_architect" ;;
        "risk_assessment") echo "risk-agent-risk_assessment" ;;
        "auditor") echo "risk-agent-auditor" ;;
        "organization_profile") echo "risk-agent-organization_profile" ;;
        *) echo "risk-agent-$1" ;;
    esac
}

# Step 2: Stop existing tasks (parallel)
echo "🔄 Stopping existing tasks..."
for agent in "${AGENTS_TO_DEPLOY[@]}"; do
    {
        SERVICE_NAME=$(get_service_name $agent)
        TASK_ARNS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --profile $AWS_PROFILE --region $AWS_REGION --query 'taskArns[]' --output text 2>/dev/null || echo "")
        if [ ! -z "$TASK_ARNS" ]; then
            for task_arn in $TASK_ARNS; do
                aws ecs stop-task --cluster $CLUSTER_NAME --task $task_arn --profile $AWS_PROFILE --region $AWS_REGION >/dev/null 2>&1 &
            done
        fi
    } &
done
wait

# Step 3: Force task definition update and service deployment
echo "📦 Updating services with latest images..."
for agent in "${AGENTS_TO_DEPLOY[@]}"; do
    {
        SERVICE_NAME=$(get_service_name $agent)
        
        # Get current task definition
        TASK_DEF=$(aws ecs describe-services \
            --cluster $CLUSTER_NAME \
            --services $SERVICE_NAME \
            --profile $AWS_PROFILE \
            --region $AWS_REGION \
            --query 'services[0].taskDefinition' \
            --output text 2>/dev/null || echo "")
        
        if [ ! -z "$TASK_DEF" ] && [ "$TASK_DEF" != "None" ]; then
            # Create new task definition revision to force image pull
            NEW_TASK_DEF=$(aws ecs describe-task-definition \
                --task-definition $TASK_DEF \
                --profile $AWS_PROFILE \
                --region $AWS_REGION \
                --query 'taskDefinition' 2>/dev/null)
            
            if [ ! -z "$NEW_TASK_DEF" ]; then
                # Register new task definition (forces new revision)
                echo "$NEW_TASK_DEF" | jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' > /tmp/taskdef_$agent.json
                
                aws ecs register-task-definition \
                    --cli-input-json file:///tmp/taskdef_$agent.json \
                    --profile $AWS_PROFILE \
                    --region $AWS_REGION >/dev/null 2>&1
                
                rm -f /tmp/taskdef_$agent.json
            fi
        fi
        
        # Update service with force new deployment
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $SERVICE_NAME \
            --force-new-deployment \
            --deployment-configuration maximumPercent=200,minimumHealthyPercent=0 \
            --profile $AWS_PROFILE \
            --region $AWS_REGION >/dev/null 2>&1
        
        echo "✓ $agent deployment triggered with latest image"
    } &
done
wait

# Step 4: Enhanced deployment verification
echo "⏳ Verifying deployments with enhanced checks..."
FAILED=()

for agent in "${AGENTS_TO_DEPLOY[@]}"; do
    SERVICE_NAME=$(get_service_name $agent)
    echo "🔍 Comprehensive verification for $agent..."
    
    # Step 1: Verify deployment completed
    if ! verify_deployment_success $agent; then
        FAILED+=($agent)
        continue
    fi
done



# Summary
echo ""
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "🎉 All agents deployed successfully!"
else
    echo "❌ Failed: ${FAILED[*]}"
    exit 1
fi