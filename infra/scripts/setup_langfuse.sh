#!/usr/bin/env bash

# Langfuse Setup Script - Simple and Working
# Provides clear instructions for the only manual step required

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

# Generate secure random password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-16
}

# Store credentials in SSM
store_credentials() {
    local email=$1
    local password=$2
    
    log "Storing admin credentials in SSM Parameter Store..."
    
    # Store email
    aws ssm put-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse/admin-email" \
        --value "$email" \
        --type "String" \
        --overwrite \
        --description "Langfuse admin email for $ENVIRONMENT" > /dev/null
    
    # Store password securely
    aws ssm put-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse/admin-password" \
        --value "$password" \
        --type "SecureString" \
        --overwrite \
        --description "Langfuse admin password for $ENVIRONMENT" > /dev/null
    
    log "Admin credentials stored securely in SSM"
}

# Create user account
create_user() {
    local langfuse_url=$1
    local email="admin@riskagent.local"
    local password=$(generate_password)
    local name="Risk Agent Admin"
    
    log "Creating user account: $email"
    
    # Try to sign up
    local signup_response=$(curl -s -X POST "$langfuse_url/api/auth/signup" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$email\",
            \"password\": \"$password\",
            \"name\": \"$name\"
        }" || true)
    
    if echo "$signup_response" | grep -q "already exists"; then
        log "User already exists, using existing account"
        # Use the existing password from SSM if available
        local existing_password=$(aws ssm get-parameter \
            --profile "$AWS_PROFILE" \
            --region us-east-1 \
            --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse/admin-password" \
            --with-decryption \
            --query 'Parameter.Value' \
            --output text 2>/dev/null || echo "RiskAgent2024!")
        password="$existing_password"
    else
        log "User created successfully"
        # Store the new credentials
        store_credentials "$email" "$password"
    fi
    
    echo "$email|$password"
}

# Wait for Langfuse to be ready
get_langfuse_url() {
    cd "$PROJECT_ROOT/infra/environments/$ENVIRONMENT"
    local output=$(./terraform-wrapper.sh output -raw agents_alb_dns_name "$AWS_PROFILE" 2>/dev/null)
    local url=$(echo "$output" | grep -E "^[a-zA-Z0-9.-]+\.elb\.amazonaws\.com$" | head -1)
    if [ -z "$url" ]; then
        error "Could not get ALB DNS name from Terraform outputs. Make sure terraform has been applied."
    fi
    echo "http://$url:3000"
}

# Wait for Langfuse to be ready
wait_for_langfuse() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    log "Waiting for Langfuse to be ready at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url/api/public/health" > /dev/null 2>&1; then
            log "Langfuse is ready!"
            return 0
        fi
        
        info "Attempt $attempt/$max_attempts - Langfuse not ready yet, waiting 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    error "Langfuse did not become ready after $max_attempts attempts"
}

# Store API keys in SSM
store_api_keys() {
    local public_key=$1
    local secret_key=$2
    
    log "Storing API keys in SSM Parameter Store..."
    
    # Store public key
    aws ssm put-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse/public-key" \
        --value "$public_key" \
        --type "String" \
        --overwrite \
        --description "Langfuse public API key for $ENVIRONMENT" > /dev/null
    
    # Store secret key
    aws ssm put-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse/secret-key" \
        --value "$secret_key" \
        --type "SecureString" \
        --overwrite \
        --description "Langfuse secret API key for $ENVIRONMENT" > /dev/null
    
    log "API keys stored successfully in SSM"
}

# Verify setup by testing API keys
verify_setup() {
    local langfuse_url=$1
    
    log "Verifying setup..."
    
    # Get keys from SSM
    local public_key=$(aws ssm get-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse/public-key" \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$public_key" ]; then
        error "Could not retrieve public key from SSM"
    fi
    
    log "API keys verified and stored successfully"
}

# Main setup function
main() {
    log "🚀 Langfuse Setup for environment: $ENVIRONMENT"
    
    # Get Langfuse URL
    local langfuse_url=$(get_langfuse_url)
    log "Langfuse URL: $langfuse_url"
    
    # Wait for Langfuse to be ready
    wait_for_langfuse "$langfuse_url"
    
    # Create user account
    create_user "$langfuse_url" > /dev/null
    
    # Get credentials for display
    local email="admin@riskagent.local"
    local password=$(aws ssm get-parameter \
        --profile "$AWS_PROFILE" \
        --region us-east-1 \
        --name "/$PROJECT_NAME/$ENVIRONMENT/langfuse/admin-password" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo "RiskAgent2024!")
    
    log "User account ready"
    
    echo ""
    echo "📋 Complete the setup:"
    echo ""
    echo "1. 🌐 Open: $langfuse_url"
    echo "2. 👤 Sign in with:"
    echo "   Email: $email"
    echo "   Password: $password"
    echo "3. 🏗️  Langfuse will auto-create your first project"
    echo "4. ⚙️  Go to Settings > API Keys"
    echo "5. 🔑 Create API keys named 'risk-agent'"
    echo "6. 💾 Run: $0 --store-keys <public-key> <secret-key>"
    echo ""
    echo "🎯 Just 4 more steps for full automation!"
}

# Handle command line arguments
case "${1:-}" in
    "--store-keys")
        if [ -n "$2" ] && [ -n "$3" ]; then
            store_api_keys "$2" "$3"
            verify_setup "$(get_langfuse_url)"
            
            langfuse_url=$(get_langfuse_url)
            
            log "✅ Setup complete!"
            echo ""
            echo "🎉 Langfuse is now fully configured!"
            echo "   URL: $langfuse_url"
            echo "   API keys stored in SSM Parameter Store"
            echo "   Environment: $ENVIRONMENT"
            echo ""
            echo "🚀 Next steps:"
            echo "1. Restart your agents to pick up the environment variables"
            echo "2. Run a risk assessment to see tracing in action"
            echo "3. Check $langfuse_url for trace data"
        else
            error "Usage: $0 --store-keys <public-key> <secret-key>"
        fi
        ;;
    "--help")
        echo "Langfuse Setup Script"
        echo ""
        echo "Usage:"
        echo "  $0                           # Show setup instructions"
        echo "  $0 --store-keys pk-... sk-... # Store API keys after manual setup"
        echo "  $0 --help                   # Show this help"
        echo ""
        echo "Environment variables:"
        echo "  ENVIRONMENT=${ENVIRONMENT}    # Target environment"
        echo "  AWS_PROFILE=${AWS_PROFILE}    # AWS profile to use"
        ;;
    *)
        main
        ;;
esac
