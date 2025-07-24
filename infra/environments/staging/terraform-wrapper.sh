#!/usr/bin/env bash

# Terraform wrapper script for staging environment
# Usage: AWS_PROFILE=your-profile ./terraform-wrapper.sh [terraform-command]

set -e

# Show usage information
show_usage() {
    echo "Terraform Wrapper for Staging Environment"
    echo ""
    echo "Usage: AWS_PROFILE=your-profile $0 [TERRAFORM_COMMAND]"
    echo ""
    echo "Description:"
    echo "  Wrapper script that handles AWS authentication, backend configuration,"
    echo "  and provides convenient shortcuts for common Terraform operations."
    echo ""
    echo "Environment Variables:"
    echo "  AWS_PROFILE     AWS profile to use (required)"
    echo ""
    echo "Common Terraform Commands:"
    echo "  init            Initialize Terraform with backend configuration"
    echo "  plan            Show execution plan"
    echo "  apply           Apply changes (with auto-approve)"
    echo "  destroy         Destroy infrastructure"
    echo "  output          Show output values"
    echo "  state           Manage Terraform state"
    echo "  validate        Validate configuration"
    echo "  fmt             Format configuration files"
    echo ""
    echo "Features:"
    echo "  • Automatic AWS SSO session validation"
    echo "  • Backend configuration handling (backend.hcl)"
    echo "  • Cross-account deployment support"
    echo "  • Auto-approve for apply commands"
    echo "  • Credential export for Terraform"
    echo ""
    echo "Prerequisites:"
    echo "  • terraform.tfvars file must exist"
    echo "  • backend.hcl file must exist"
    echo "  • AWS CLI configured with SSO profiles"
    echo "  • Active SSO session for the specified profile"
    echo ""
    echo "Examples:"
    echo "  AWS_PROFILE=staging-admin $0 init        # Initialize with backend config"
    echo "  AWS_PROFILE=staging-admin $0 plan        # Show execution plan"
    echo "  AWS_PROFILE=staging-admin $0 apply       # Apply changes (auto-approved)"
    echo "  AWS_PROFILE=staging-admin $0 output      # Show outputs"
    echo "  AWS_PROFILE=staging-admin $0 destroy     # Destroy infrastructure"
    echo ""
    echo "SSO Login:"
    echo "  If SSO session is expired, run:"
    echo "  aws sso login --profile your-profile"
}

# Parse command line arguments for help
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_usage
    exit 0
fi

# Check if AWS profile is provided via environment variable
if [ -z "$AWS_PROFILE" ]; then
    echo "ERROR: AWS_PROFILE environment variable is required!"
    echo "Usage: AWS_PROFILE=your-profile $0 [terraform-command]"
    echo "Example: AWS_PROFILE=my-profile $0 plan"
    echo "Example: AWS_PROFILE=my-profile $0 apply"
    exit 1
fi

# Use AWS_PROFILE environment variable
AWS_PROFILE_NAME="$AWS_PROFILE"

# Validate profile exists
if ! aws configure list-profiles | grep -q "^$AWS_PROFILE_NAME$"; then
    echo "ERROR: AWS profile '$AWS_PROFILE_NAME' not found!"
    echo "Available profiles:"
    aws configure list-profiles
    exit 1
fi
export AWS_PROFILE=$AWS_PROFILE_NAME

echo "Using AWS Profile: $AWS_PROFILE_NAME"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "ERROR: terraform.tfvars not found!"
    echo "Please ensure terraform.tfvars exists with staging configuration"
    exit 1
fi

# Check if backend.hcl exists
if [ ! -f "backend.hcl" ]; then
    echo "ERROR: backend.hcl not found!"
    echo "Please ensure backend.hcl exists with staging configuration"
    exit 1
fi

# Get temporary credentials from SSO session
echo "Getting temporary credentials from SSO session..."
CREDS=$(aws sts get-caller-identity --profile $AWS_PROFILE_NAME 2>/dev/null || {
    echo "SSO session expired or not found. Please run: aws sso login --profile $AWS_PROFILE_NAME"
    exit 1
})

echo "Using AWS Account: $(echo $CREDS | jq -r '.Account')"
echo "Using AWS User: $(echo $CREDS | jq -r '.Arn')"

# Export credentials for Terraform
eval $(aws configure export-credentials --profile $AWS_PROFILE_NAME --format env)

# Handle init command with backend config
if [ "$1" = "init" ]; then
    # Check if this is a cross-account deployment (different backend)
    if [ -f ".terraform/terraform.tfstate" ]; then
        echo "Existing state detected - using -reconfigure for cross-account deployment"
        echo "Running: terraform init -reconfigure -backend-config=backend.hcl"
        terraform init -reconfigure -backend-config=backend.hcl
    else
        echo "Running: terraform init -backend-config=backend.hcl"
        terraform init -backend-config=backend.hcl
    fi
else
    # Add auto-approve for apply commands
    if [ "$1" = "apply" ]; then
        echo "Running: terraform apply -auto-approve"
        terraform apply -auto-approve
    else
        echo "Running: terraform $@"
        terraform "$@"
    fi
fi