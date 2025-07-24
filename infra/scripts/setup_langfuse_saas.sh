#!/usr/bin/env bash

# Langfuse SaaS Setup Script
# Helps migrate from self-hosted to SaaS version

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
ENVIRONMENT=${ENVIRONMENT:-staging}
AWS_PROFILE=${AWS_PROFILE:-""}
PROJECT_NAME="risk-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Store SaaS credentials in SSM
store_saas_credentials() {
    local public_key=$1
    local secret_key=$2
    
    log "Storing SaaS API keys in SSM Parameter Store..."
    
    # Store public key
    aws ssm put-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse-saas/public-key" \
        --value "$public_key" \
        --type "String" \
        --overwrite \
        --description "Langfuse SaaS public API key for $ENVIRONMENT" > /dev/null
    
    # Store secret key
    aws ssm put-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse-saas/secret-key" \
        --value "$secret_key" \
        --type "SecureString" \
        --overwrite \
        --description "Langfuse SaaS secret API key for $ENVIRONMENT" > /dev/null
    
    log "SaaS API keys stored successfully in SSM"
}

# Update ECS tasks with SSM parameters
update_ecs_configuration() {
    log "Updating ECS task definitions to use SSM parameters..."
    
    # Get the SSM parameter ARNs
    local public_key_param="/$PROJECT_NAME/$ENVIRONMENT/langfuse-saas/public-key"
    local secret_key_param="/$PROJECT_NAME/$ENVIRONMENT/langfuse-saas/secret-key"
    
    # Update terraform.tfvars to use SSM parameters
    cd "$PROJECT_ROOT/infra/environments/$ENVIRONMENT"
    
    # Add SSM parameter references to terraform.tfvars
    if ! grep -q "langfuse_saas_public_key_parameter" terraform.tfvars; then
        cat >> terraform.tfvars << EOF

# Langfuse SaaS SSM Parameters
langfuse_saas_public_key_parameter = "$public_key_param"
langfuse_saas_secret_key_parameter = "$secret_key_param"
EOF
    fi
    
    log "ECS configuration updated to use SSM parameters"
}

# Apply terraform changes
apply_terraform() {
    log "Applying terraform changes..."
    
    cd "$PROJECT_ROOT/infra/environments/$ENVIRONMENT"
    
    # Plan first
    info "Running terraform plan..."
    ./terraform-wrapper.sh plan "$AWS_PROFILE"
    
    # Ask for confirmation
    echo ""
    read -p "Apply these changes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./terraform-wrapper.sh apply "$AWS_PROFILE"
        log "Terraform changes applied successfully"
    else
        warn "Terraform apply cancelled"
        return 1
    fi
}

# Restart agent services
restart_agents() {
    log "Restarting agent services to pick up new configuration..."
    
    cd "$PROJECT_ROOT/agents/deploy"
    ENVIRONMENT="$ENVIRONMENT" ./deploy_ecs.sh all
    
    log "Agent services restarted successfully"
}

# Verify SaaS setup
verify_setup() {
    log "Verifying SaaS setup..."
    
    # Check if keys are in SSM
    local public_key=$(aws ssm get-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse-saas/public-key" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$public_key" ] || [ "$public_key" = "PLACEHOLDER_SET_AFTER_CLOUD_SETUP" ]; then
        error "SaaS public key not found in SSM or still placeholder"
    fi
    
    log "SaaS setup verified successfully"
    
    echo ""
    echo "🎉 Langfuse SaaS migration complete!"
    echo "   Environment: $ENVIRONMENT"
    echo "   SaaS Host: https://cloud.langfuse.com"
    echo "   API keys stored in SSM Parameter Store"
    echo ""
    echo "🚀 Next steps:"
    echo "1. Run a risk assessment to test tracing"
    echo "2. Check https://cloud.langfuse.com for trace data"
    echo "3. Monitor agent logs for successful Langfuse initialization"
}

# Main setup function
main() {
    log "🚀 Langfuse SaaS Migration for environment: $ENVIRONMENT"
    
    echo ""
    echo "📋 Migration Steps:"
    echo "1. 🌐 Create account at https://cloud.langfuse.com"
    echo "2. 🏗️  Create project: 'risk-agent-$ENVIRONMENT'"
    echo "3. 🔑 Generate API keys"
    echo "4. 💾 Store keys using: $0 --store-keys <public-key> <secret-key>"
    echo "5. 🚀 Deploy: $0 --deploy"
    echo ""
    echo "💡 Free tier includes 50k observations/month"
    echo "💰 Estimated savings: \$95-170/month vs self-hosted"
}

# Handle command line arguments
case "${1:-}" in
    "--store-keys")
        if [ -n "$2" ] && [ -n "$3" ]; then
            store_saas_credentials "$2" "$3"
            log "✅ API keys stored! Run '$0 --deploy' to complete migration"
        else
            error "Usage: $0 --store-keys <public-key> <secret-key>"
        fi
        ;;
    "--deploy")
        log "Starting deployment phase..."
        update_ecs_configuration
        apply_terraform
        restart_agents
        verify_setup
        ;;
    "--verify")
        verify_setup
        ;;
    "--help")
        echo "Langfuse SaaS Migration Script"
        echo ""
        echo "Usage:"
        echo "  $0                                    # Show migration instructions"
        echo "  $0 --store-keys pk-... sk-...       # Store SaaS API keys"
        echo "  $0 --deploy                          # Deploy SaaS configuration"
        echo "  $0 --verify                          # Verify setup"
        echo "  $0 --help                            # Show this help"
        echo ""
        echo "Environment variables:"
        echo "  ENVIRONMENT=${ENVIRONMENT}    # Target environment"
        echo "  AWS_PROFILE=${AWS_PROFILE}    # AWS profile to use"
        ;;
    *)
        main
        ;;
esac
