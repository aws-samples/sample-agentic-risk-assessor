#!/usr/bin/env bash

# Cross-Account Deployment Script for RiskAgent.Agentic
# Usage: ./deploy_cross_account.sh <target-account-id> <aws-profile> [region] [auto-approve]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <target-account-id> <aws-profile> [region] [auto-approve]"
    echo "Example: $0 123456789012 my-target-profile us-east-1 auto-approve"
    echo "         $0 123456789012 my-target-profile us-east-1"
    exit 1
fi

TARGET_ACCOUNT_ID=$1
AWS_PROFILE_NAME=$2
REGION=${3:-us-east-1}
AUTO_APPROVE=${4:-false}

print_status "🚀 Starting cross-account deployment to account: $TARGET_ACCOUNT_ID"
print_status "📍 Using AWS profile: $AWS_PROFILE_NAME"
print_status "🌍 Deploying to region: $REGION"
if [ "$AUTO_APPROVE" = "auto-approve" ]; then
    print_warning "⚡ Auto-approve mode enabled - no user prompts"
fi

# Set environment variables
export AWS_ACCOUNT_ID=$TARGET_ACCOUNT_ID
export AWS_PROFILE=$AWS_PROFILE_NAME
export AWS_REGION=$REGION

# Navigate to terraform directory
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR/../terraform"

# Function to generate unique Cognito domain prefix
generate_cognito_domain() {
    local account_id=$1
    local timestamp=$(date +%s)
    echo "risk-agent-${account_id}-${timestamp}"
}

# Check if configuration files exist
if [ ! -f "terraform.tfvars" ]; then
    print_status "❌ terraform.tfvars not found. Creating from template..."
    
    if [ ! -f "terraform.tfvars.example" ]; then
        print_error "❌ terraform.tfvars.example not found!"
        exit 1
    fi
    
    cp terraform.tfvars.example terraform.tfvars
    
    # Generate unique Cognito domain prefix
    COGNITO_DOMAIN=$(generate_cognito_domain $TARGET_ACCOUNT_ID)
    
    # Update with provided values
    sed -i.bak "s/123456789012/$TARGET_ACCOUNT_ID/g" terraform.tfvars
    sed -i.bak "s/target-account-profile/$AWS_PROFILE_NAME/g" terraform.tfvars
    sed -i.bak "s/us-east-1/$REGION/g" terraform.tfvars
    sed -i.bak "s/risk-agent-cognito-domain/$COGNITO_DOMAIN/g" terraform.tfvars
    
    print_success "✅ Created terraform.tfvars with unique Cognito domain: $COGNITO_DOMAIN"
    rm -f terraform.tfvars.bak
else
    print_success "✅ terraform.tfvars already exists"
fi

if [ ! -f "backend.hcl" ]; then
    print_status "❌ backend.hcl not found. Creating from template..."
    
    if [ ! -f "backend.hcl.example" ]; then
        print_error "❌ backend.hcl.example not found!"
        exit 1
    fi
    
    cp backend.hcl.example backend.hcl
    
    # Update with provided values
    sed -i.bak "s/123456789012/$TARGET_ACCOUNT_ID/g" backend.hcl
    sed -i.bak "s/target-account-profile/$AWS_PROFILE_NAME/g" backend.hcl
    sed -i.bak "s/us-east-1/$REGION/g" backend.hcl
    
    print_success "✅ Created backend.hcl"
    rm -f backend.hcl.bak
else
    print_success "✅ backend.hcl already exists"
fi

# Verify AWS credentials
print_status "🔐 Verifying AWS credentials..."
CREDS_OUTPUT=$(aws sts get-caller-identity --profile $AWS_PROFILE_NAME 2>&1) || {
    print_error "❌ Failed to get AWS credentials."
    print_error "Please run: aws sso login --profile $AWS_PROFILE_NAME"
    exit 1
}

print_success "✅ AWS credentials verified"
echo "$CREDS_OUTPUT"

# Verify account ID matches
ACTUAL_ACCOUNT=$(echo "$CREDS_OUTPUT" | jq -r '.Account' 2>/dev/null || echo "unknown")
if [ "$ACTUAL_ACCOUNT" != "$TARGET_ACCOUNT_ID" ]; then
    print_error "❌ Account ID mismatch!"
    print_error "   Expected: $TARGET_ACCOUNT_ID"
    print_error "   Actual: $ACTUAL_ACCOUNT"
    exit 1
fi

# Create S3 bucket and DynamoDB table for Terraform state if they don't exist
print_status "🪣 Setting up Terraform state management..."
S3_BUCKET="risk-agent-terraform-state-$TARGET_ACCOUNT_ID"
DYNAMODB_TABLE="risk-agent-terraform-locks-$TARGET_ACCOUNT_ID"

# Create S3 bucket if it doesn't exist
print_status "Checking S3 bucket: $S3_BUCKET"
if ! aws s3api head-bucket --bucket $S3_BUCKET --profile $AWS_PROFILE_NAME 2>/dev/null; then
    print_status "Creating S3 bucket: $S3_BUCKET"
    
    # Handle region-specific bucket creation
    CREATE_BUCKET_OUTPUT=""
    if [ "$REGION" = "us-east-1" ]; then
        CREATE_BUCKET_OUTPUT=$(aws s3api create-bucket --bucket $S3_BUCKET --profile $AWS_PROFILE_NAME 2>&1) || {
            print_error "❌ Failed to create S3 bucket: $S3_BUCKET"
            print_error "Error: $CREATE_BUCKET_OUTPUT"
            print_error ""
            print_error "🔧 Required permissions for $AWS_PROFILE_NAME:"
            print_error "   - s3:CreateBucket"
            print_error "   - s3:PutBucketVersioning"
            print_error "   - s3:PutBucketEncryption"
            print_error "   - s3:PutBucketPublicAccessBlock"
            print_error "   - dynamodb:CreateTable"
            print_error "   - dynamodb:DescribeTable"
            print_error ""
            print_error "💡 Please ask your AWS administrator to grant these permissions or create:"
            print_error "   - S3 Bucket: $S3_BUCKET (with versioning and encryption)"
            print_error "   - DynamoDB Table: $DYNAMODB_TABLE (with LockID as hash key)"
            exit 1
        }
    else
        CREATE_BUCKET_OUTPUT=$(aws s3api create-bucket --bucket $S3_BUCKET --profile $AWS_PROFILE_NAME --region $REGION --create-bucket-configuration LocationConstraint=$REGION 2>&1) || {
            print_error "❌ Failed to create S3 bucket: $S3_BUCKET"
            print_error "Error: $CREATE_BUCKET_OUTPUT"
            print_error ""
            print_error "🔧 Required permissions for $AWS_PROFILE_NAME:"
            print_error "   - s3:CreateBucket"
            print_error "   - s3:PutBucketVersioning"
            print_error "   - s3:PutBucketEncryption"
            print_error "   - s3:PutBucketPublicAccessBlock"
            print_error "   - dynamodb:CreateTable"
            print_error "   - dynamodb:DescribeTable"
            print_error ""
            print_error "💡 Please ask your AWS administrator to grant these permissions or create:"
            print_error "   - S3 Bucket: $S3_BUCKET (with versioning and encryption)"
            print_error "   - DynamoDB Table: $DYNAMODB_TABLE (with LockID as hash key)"
            exit 1
        }
    fi
    
    # Enable versioning
    aws s3api put-bucket-versioning --bucket $S3_BUCKET --versioning-configuration Status=Enabled --profile $AWS_PROFILE_NAME || {
        print_warning "⚠️ Failed to enable versioning on S3 bucket (continuing anyway)"
    }
    
    # Enable encryption
    aws s3api put-bucket-encryption --bucket $S3_BUCKET --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }' --profile $AWS_PROFILE_NAME || {
        print_warning "⚠️ Failed to enable encryption on S3 bucket (continuing anyway)"
    }
    
    # Block public access
    aws s3api put-public-access-block --bucket $S3_BUCKET --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" --profile $AWS_PROFILE_NAME || {
        print_warning "⚠️ Failed to block public access on S3 bucket (continuing anyway)"
    }
    
    print_success "✅ S3 bucket created and configured"
else
    print_success "✅ S3 bucket $S3_BUCKET already exists"
fi

# Create DynamoDB table if it doesn't exist
print_status "Checking DynamoDB table: $DYNAMODB_TABLE"
if ! aws dynamodb describe-table --table-name $DYNAMODB_TABLE --profile $AWS_PROFILE_NAME --region $REGION 2>/dev/null; then
    print_status "Creating DynamoDB table: $DYNAMODB_TABLE"
    CREATE_TABLE_OUTPUT=$(aws dynamodb create-table \
        --table-name $DYNAMODB_TABLE \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --profile $AWS_PROFILE_NAME \
        --region $REGION 2>&1) || {
        print_error "❌ Failed to create DynamoDB table: $DYNAMODB_TABLE"
        print_error "Error: $CREATE_TABLE_OUTPUT"
        print_error ""
        print_error "🔧 Required permissions for $AWS_PROFILE_NAME:"
        print_error "   - dynamodb:CreateTable"
        print_error "   - dynamodb:DescribeTable"
        print_error ""
        print_error "💡 Please ask your AWS administrator to create:"
        print_error "   - DynamoDB Table: $DYNAMODB_TABLE"
        print_error "   - Primary Key: LockID (String)"
        print_error "   - Provisioned throughput: 5 RCU, 5 WCU"
        exit 1
    }
    
    print_status "Waiting for DynamoDB table to be active..."
    aws dynamodb wait table-exists --table-name $DYNAMODB_TABLE --profile $AWS_PROFILE_NAME --region $REGION || {
        print_warning "⚠️ Timeout waiting for table to be active (continuing anyway)"
    }
    print_success "✅ DynamoDB table created and active"
else
    print_success "✅ DynamoDB table $DYNAMODB_TABLE already exists"
fi

# Initialize Terraform with backend configuration
print_status "🔧 Initializing Terraform..."
if ! ./terraform-wrapper.sh init $AWS_PROFILE_NAME; then
    print_error "❌ Terraform initialization failed"
    exit 1
fi
print_success "✅ Terraform initialized successfully"

# Plan deployment
print_status "📋 Planning deployment..."
if ! ./terraform-wrapper.sh plan $AWS_PROFILE_NAME; then
    print_error "❌ Terraform plan failed"
    exit 1
fi
print_success "✅ Terraform plan completed successfully"

# Ask for confirmation unless auto-approve is set
if [ "$AUTO_APPROVE" != "auto-approve" ]; then
    echo
    print_warning "🤔 Do you want to proceed with deployment?"
    print_warning "   This will create AWS resources in account $TARGET_ACCOUNT_ID"
    read -p "   Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "❌ Deployment cancelled by user"
        exit 0
    fi
else
    print_warning "⚡ Auto-approve mode - proceeding with deployment"
fi

# Apply deployment
print_status "🚀 Deploying infrastructure..."
if ! ./terraform-wrapper.sh apply -auto-approve $AWS_PROFILE_NAME; then
    print_error "❌ Terraform apply failed"
    exit 1
fi

print_success "✅ Cross-account deployment completed successfully!"
echo
print_status "📝 Next steps:"
print_status "   1. Deploy Lambda functions: cd ../../ && ./infra/scripts/deploy_lambdas_unified.sh all deploy"
print_status "   2. Deploy agents: cd ../../ && ./agents/deploy/deploy_ecs.sh all"
print_status "   3. Update frontend environment variables with new URLs"
echo
print_status "📊 Getting deployment outputs..."
./terraform-wrapper.sh output $AWS_PROFILE_NAME