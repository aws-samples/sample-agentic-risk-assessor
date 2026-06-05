#!/bin/bash

# Terraform Wrapper Script for Modular Infrastructure
# Usage: ./terraform-wrapper-new.sh [environment] [command] [options]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENTS_DIR="${SCRIPT_DIR}/environments"

# SSL/TLS configuration for AWS CLI
export PYTHONHTTPSVERIFY=0
export AWS_CLI_AUTO_PROMPT=off

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
Usage: $0 [environment] [command] [options]

Environments:
  dev      - Development environment
  staging  - Staging environment  
  prod     - Production environment

Commands:
  init     - Initialize Terraform
  plan     - Create execution plan
  apply    - Apply changes
  destroy  - Destroy infrastructure
  validate - Validate configuration
  fmt      - Format configuration files

Options:
  -auto-approve  - Auto approve apply/destroy
  -target=<resource>  - Target specific resource
  -var-file=<file>    - Use specific tfvars file

Examples:
  $0 prod init
  $0 prod plan
  $0 prod apply -auto-approve
  $0 dev destroy -target=module.lambda
EOF
}

validate_environment() {
    local env=$1
    if [[ ! -d "${ENVIRONMENTS_DIR}/${env}" ]]; then
        log_error "Environment '${env}' not found in ${ENVIRONMENTS_DIR}"
        log_info "Available environments: $(ls ${ENVIRONMENTS_DIR} | tr '\n' ' ')"
        exit 1
    fi
}

# Main script
if [[ $# -lt 2 ]]; then
    show_usage
    exit 1
fi

ENVIRONMENT=$1
COMMAND=$2
shift 2
OPTIONS="$@"

# Validate environment
validate_environment "${ENVIRONMENT}"

# Set working directory
WORK_DIR="${ENVIRONMENTS_DIR}/${ENVIRONMENT}"
cd "${WORK_DIR}"

log_info "Working in environment: ${ENVIRONMENT}"
log_info "Working directory: ${WORK_DIR}"

# Execute Terraform command
case "${COMMAND}" in
    init)
        log_info "Initializing Terraform for ${ENVIRONMENT}..."
        terraform init -backend-config=backend.hcl ${OPTIONS}
        log_success "Terraform initialized successfully"
        ;;
    
    plan)
        log_info "Creating execution plan for ${ENVIRONMENT}..."
        terraform plan ${OPTIONS}
        ;;
    
    apply)
        log_info "Applying changes to ${ENVIRONMENT}..."
        terraform apply ${OPTIONS}
        if [[ $? -eq 0 ]]; then
            log_success "Changes applied successfully to ${ENVIRONMENT}"
        fi
        ;;
    
    destroy)
        log_warning "Destroying infrastructure in ${ENVIRONMENT}..."
        terraform destroy ${OPTIONS}
        if [[ $? -eq 0 ]]; then
            log_success "Infrastructure destroyed in ${ENVIRONMENT}"
        fi
        ;;
    
    validate)
        log_info "Validating configuration for ${ENVIRONMENT}..."
        terraform validate
        log_success "Configuration is valid"
        ;;
    
    fmt)
        log_info "Formatting Terraform files..."
        terraform fmt -recursive "${SCRIPT_DIR}"
        log_success "Files formatted successfully"
        ;;
    
    *)
        log_error "Unknown command: ${COMMAND}"
        show_usage
        exit 1
        ;;
esac