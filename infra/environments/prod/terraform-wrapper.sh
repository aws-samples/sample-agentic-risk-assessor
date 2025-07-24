#!/bin/bash

# Terraform wrapper script for prod environment
# Usage: ./terraform-wrapper.sh [terraform-command] [aws-profile]

set -e

# AWS profile must be provided as last argument
if [ $# -lt 2 ]; then
    echo "ERROR: AWS profile is required!"
    echo "Usage: $0 [terraform-command] [aws-profile]"
    echo "Example: $0 plan riskagent"
    echo "Example: $0 apply riskagent"
    exit 1
fi

# Get AWS profile from last argument
AWS_PROFILE_NAME="${!#}"
# Remove profile from arguments
set -- "${@:1:$(($#-1))}"

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
    echo "Please ensure terraform.tfvars exists with prod configuration"
    exit 1
fi

# Check if backend.hcl exists
if [ ! -f "backend.hcl" ]; then
    echo "ERROR: backend.hcl not found!"
    echo "Please ensure backend.hcl exists with prod configuration"
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