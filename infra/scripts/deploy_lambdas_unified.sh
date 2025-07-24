#!/usr/bin/env bash

# Unified Lambda Deployment Script
# Handles all Lambda functions, layers, build, and deployment
# Usage: ./deploy_lambdas_unified.sh [TARGET] [ACTION] [AWS_PROFILE]
# Help:  ./deploy_lambdas_unified.sh --help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Config
AWS_PROFILE=${3:-${AWS_PROFILE}}
AWS_REGION=us-east-1
PROJECT_ROOT=$(pwd)
LAMBDA_DIR="$PROJECT_ROOT/lambda"
TEMP_DIR="$PROJECT_ROOT/temp/lambda_packages"
DEPENDENCIES_DIR="$PROJECT_ROOT/dependencies"

# Deployment tracking
FAILED_DEPLOYMENTS=()

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }


# Error handling helper function
aws_cmd() {
    local cmd_description="$1"
    shift
    
    if output=$("$@" 2>&1); then
        # Extract useful info from success responses
        if echo "$output" | jq -e '.Version' >/dev/null 2>&1; then
            version=$(echo "$output" | jq -r '.Version')
            echo "✅ $cmd_description completed (version: $version)"
        else
            echo "✅ $cmd_description completed"
        fi
        return 0
    else
        echo "❌ $cmd_description failed:"
        # Show specific AWS error if available
        if echo "$output" | jq -e '.errorMessage' >/dev/null 2>&1; then
            echo "$output" | jq -r '.errorMessage'
        else
            echo "$output" | head -5
        fi
        return 1
    fi
}


# Ensure all required directories exist
mkdir -p "$TEMP_DIR"
mkdir -p "$DEPENDENCIES_DIR"
mkdir -p "$LAMBDA_DIR"
mkdir -p "$PROJECT_ROOT/system_prompts"

# Create lambda function subdirectories if they don't exist
for func in "${CONSOLIDATED_FUNCTIONS[@]}" "${SIMPLE_FUNCTIONS[@]}" "${COMPLEX_FUNCTIONS[@]}"; do
    mkdir -p "$LAMBDA_DIR/$func"
done

# Install dependencies if directory is empty
if [[ ! -d "$DEPENDENCIES_DIR/opensearchpy" ]] || [[ ! -d "$DEPENDENCIES_DIR/requests_aws4auth" ]]; then
    echo "📦 Installing OpenSearch dependencies..."
    
    # Create temporary virtual environment for OpenSearch dependencies
    local opensearch_venv="$TEMP_DIR/opensearch_venv_$$"
    python3.11 -m venv "$opensearch_venv" >/dev/null 2>&1
    source "$opensearch_venv/bin/activate"
    
    # Install in virtual environment then copy
    pip install opensearch-py requests-aws4auth --quiet >/dev/null 2>&1
    
    # Copy packages to dependencies directory
    local site_packages="$opensearch_venv/lib/python"*/site-packages
    cp -r "$site_packages/opensearchpy" "$DEPENDENCIES_DIR/" 2>/dev/null || true
    cp -r "$site_packages/requests_aws4auth" "$DEPENDENCIES_DIR/" 2>/dev/null || true
    
    # Cleanup
    deactivate
    rm -rf "$opensearch_venv"
fi

# Lambda function categories
# Consolidated functions (new)
CONSOLIDATED_FUNCTIONS=(
    "document_manager"        # Replaces: get_document, get_document_content, process_document
    "assessment_retriever"    # Replaces: get_risk_assessments, get_security_assessments, get_architecture_reviews
    "assessment_content"      # Replaces: get_*_content functions
    "assessment_downloader"   # Replaces: download_risk_assessment, download_security_assessment, download_architecture_review
    "assessment_saver"        # Replaces: save_risk_assessment, save_security_assessment, save_architecture_review, save_control_gap_assessment
    "diagram_analysis"
)

# Legacy functions (to be phased out)
SIMPLE_FUNCTIONS=(
    "admin_add_service" "admin_execution_status" "admin_run_mapping" 
    "admin_run_service_mapping" "admin_services"
    "check_batch_completion" "check_bedrock_jobs"
    "create_session" "discover_framework_controls"
    "get_batch_services" "get_diagram_url" "get_node_controls"
    "get_node_details" "health" "images"
    "invoke_bedrock" "manage_services" "map_controls"
    "get_security_assessment"
    "get_sessions" "delete_session" "get_agent_capabilities"
    "perform_security_assessment" "process_bedrock_results" "process_node_controls" 
    "process_results" "process_s3_files"
    "projects" "read_services" "restart_system" "service_token_manager" "update_flow" "update_node" "upload_image"
    # Organization Profile Lambda functions
    "create_profile" "update_profile" "get_profile" "list_profiles" "delete_profile" "search_context"
    # Control mapping Lambda functions
    "resolve_control_details" "retrieve_framework_s3_data" "discover_service_capabilities"
    "process_single_control" "invoke_bedrock_rag" "combine_controls_capabilities"
    "mark_service_complete" "admin_run_service_mapping" "admin_run_mapping"
    "generate_control_reference"
    "serve_control_reference"
    "admin_execution_status" "admin_services" "admin_add_service"
    "assessment_content" "assessment_downloader" "assessment_retriever" "assessment_saver"
    "document_manager"
)

COMPLEX_FUNCTIONS=(
    "process_word_document" # Needs pandoc layer
)

# Admin functions that use lambda_functions.zip
ADMIN_FUNCTIONS=(
    # No admin API functions - all admin functions are in SIMPLE_FUNCTIONS
)

LAYERS=(
    "opensearch"  # OpenSearch + requests_aws4auth
    "pandoc"      # Pandoc binary layer
)

# System prompts to upload
SYSTEM_PROMPTS=(
    "MappingPrompts.json"     # Framework mapping prompts
    "ControlMappingPrompt.json" # Control mapping prompts
    "FrameworkConfig.json"     # Framework configuration
)

# Global shared dependencies cache
SHARED_DEPS_DIR="$TEMP_DIR/shared_dependencies"
SHARED_DEPS_INSTALLED=false

# Install shared dependencies once and cache them
install_shared_dependencies() {
    # Use requirements.lock if available (much faster), otherwise fall back to requirements.txt
    local requirements_file="$LAMBDA_DIR/requirements.lock"
    if [[ ! -f "$requirements_file" ]]; then
        requirements_file="$LAMBDA_DIR/requirements.txt"
    fi
    
    if [[ -f "$requirements_file" ]] && [[ "$SHARED_DEPS_INSTALLED" == false ]]; then
        echo "📦 Installing shared dependencies ONCE from $(basename $requirements_file)..."
        
        # Create shared cache directory
        rm -rf "$SHARED_DEPS_DIR"
        mkdir -p "$SHARED_DEPS_DIR"
        
        # Create a temporary virtual environment
        local venv_dir="$TEMP_DIR/shared_venv_$$"
        echo "   Creating virtual environment..."
        python3.11 -m venv "$venv_dir"
        
        # Activate virtual environment and install dependencies
        source "$venv_dir/bin/activate"
        echo "   Installing packages (this may take a few minutes)..."
        pip install -r "$requirements_file" --progress-bar on
        
        echo "   Caching packages for reuse..."
        # Copy installed packages to shared cache (excluding standard library)
        local site_packages=$(echo "$venv_dir/lib/python"*/site-packages)
        for pkg_dir in "$site_packages"/*; do
            if [[ -d "$pkg_dir" ]] && [[ ! "$pkg_dir" =~ (pip|setuptools|wheel|distutils|pkg_resources) ]]; then
                cp -r "$pkg_dir" "$SHARED_DEPS_DIR/" 2>/dev/null || true
            fi
        done
        
        # Copy .dist-info directories for package metadata
        for info_dir in "$site_packages"/*.dist-info; do
            if [[ -d "$info_dir" ]] && [[ ! "$info_dir" =~ (pip|setuptools|wheel) ]]; then
                cp -r "$info_dir" "$SHARED_DEPS_DIR/" 2>/dev/null || true
            fi
        done
        
        # Deactivate and cleanup virtual environment
        deactivate
        rm -rf "$venv_dir"
        
        # Remove packages provided by layers from cache
        echo "🧹 Removing layer-provided packages from cache..."
        rm -rf "$SHARED_DEPS_DIR/pydantic"*
        rm -rf "$SHARED_DEPS_DIR/instructor"*
        
        SHARED_DEPS_INSTALLED=true
        success "Shared dependencies cached and ready for reuse"
    fi
}

# Copy shared dependencies to Lambda package
install_dependencies() {
    local func_name=$1
    local package_dir=$2
    
    # Ensure shared dependencies are installed
    install_shared_dependencies
    
    if [[ -d "$SHARED_DEPS_DIR" ]]; then
        echo "📦 Copying shared dependencies to $func_name..."
        cp -r "$SHARED_DEPS_DIR"/* "$package_dir/" 2>/dev/null || true
        echo "✅ Dependencies installed for $func_name (from cache)"
    fi
}

# Build consolidated Lambda function with shared dependencies
build_consolidated_function() {
    local func_name=$1
    local src_file="$LAMBDA_DIR/${func_name}.py"
    local zip_file="$TEMP_DIR/${func_name}.zip"
    
    if [[ ! -f "$src_file" ]]; then
        warn "Source file not found: $src_file"
        return 1
    fi
    
    echo "🔨 Building consolidated function $func_name..."
    
    # Create temporary package directory
    local package_dir="$TEMP_DIR/package_${func_name}"
    mkdir -p "$package_dir"
    
    # Install dependencies if requirements.txt exists
    install_dependencies "$func_name" "$package_dir"
    
    # Copy function file
    cp "$src_file" "$package_dir/"
    
    # Copy shared directory
    if [[ -d "$LAMBDA_DIR/shared" ]]; then
        cp -r "$LAMBDA_DIR/shared" "$package_dir/"
    fi
    
    # Remove existing zip file and create new zip file
    cd "$package_dir"
    rm -f "$zip_file"
    zip -r "$zip_file" . -q
    cd - > /dev/null
    
    # Cleanup package directory
    rm -rf "$package_dir"
    
    echo "✅ $func_name built with shared dependencies"
}

# Build simple Lambda function
build_simple_function() {
    local func_name=$1
    local src_file="$LAMBDA_DIR/${func_name}.py"
    local zip_file="$TEMP_DIR/${func_name}.zip"
    local requirements_file="$LAMBDA_DIR/requirements.txt"
    
    if [[ ! -f "$src_file" ]]; then
        warn "Source file not found: $src_file"
        return 1
    fi
    
    echo "🔨 Building $func_name..."
    
    # Check if requirements.txt exists for this function
    if [[ -f "$requirements_file" ]]; then
        # Create temporary package directory for functions with dependencies
        local package_dir="$TEMP_DIR/package_${func_name}"
        mkdir -p "$package_dir"
        
        # Install dependencies
        install_dependencies "$func_name" "$package_dir"
        
        # Copy function file
        cp "$src_file" "$package_dir/"
        
        # Copy shared directory
        if [[ -d "$LAMBDA_DIR/shared" ]]; then
            cp -r "$LAMBDA_DIR/shared" "$package_dir/"
        fi
        
        # Create zip file
        cd "$package_dir"
        zip -r "$zip_file" . -q
        cd - > /dev/null
        
        # Cleanup package directory
        rm -rf "$package_dir"
    else
        # Simple zip for functions without dependencies
        zip -j "$zip_file" "$src_file" >/dev/null 2>&1
    fi
    
    echo "✅ $func_name built and packaged"
}

# Build pandoc layer with pypandoc
build_pandoc_layer() {
    local layer_zip="$TEMP_DIR/pandoc_layer.zip"
    echo "🔨 Building pandoc layer with pypandoc..."
    
    # Create temporary layer structure
    local layer_dir="$TEMP_DIR/pandoc_layer_build"
    mkdir -p "$layer_dir/bin"
    mkdir -p "$layer_dir/python"
    
    # Download and extract pandoc binary
    if [[ ! -f "$layer_dir/bin/pandoc" ]]; then
        echo "📥 Downloading pandoc binary..."
        cd "$layer_dir" || error "Failed to cd to $layer_dir"
        curl -L https://github.com/jgm/pandoc/releases/download/3.1.8/pandoc-3.1.8-linux-amd64.tar.gz | tar xz
        cp pandoc-3.1.8/bin/pandoc bin/
        rm -rf pandoc-3.1.8
        cd "$PROJECT_ROOT" || error "Failed to cd to $PROJECT_ROOT"
    fi
    
    # Install pypandoc Python package
    echo "📦 Installing pypandoc Python package..."
    
    # Create temporary virtual environment for pypandoc
    local pandoc_venv="$TEMP_DIR/pandoc_venv_$$"
    python3.11 -m venv "$pandoc_venv" >/dev/null 2>&1
    source "$pandoc_venv/bin/activate"
    
    # Install in virtual environment then copy
    pip install pypandoc --quiet >/dev/null 2>&1
    
    # Copy packages to layer directory
    local site_packages="$pandoc_venv/lib/python"*/site-packages
    cp -r "$site_packages"/* "$layer_dir/python/" 2>/dev/null || true
    
    # Cleanup
    deactivate
    rm -rf "$pandoc_venv"
    
    # Create layer zip
    cd "$layer_dir" || error "Failed to cd to $layer_dir"
    zip -r "$layer_zip" . >/dev/null 2>&1
    cd "$PROJECT_ROOT" || error "Failed to cd to $PROJECT_ROOT"
    
    # Cleanup
    rm -rf "$layer_dir"
    
    echo "✅ Pandoc layer built with pypandoc"
}

# Build process_word_document with pandoc layer
build_process_word_document() {
    local func_name="process_word_document"
    local zip_file="$TEMP_DIR/process_word_document.zip"
    local requirements_file="$LAMBDA_DIR/requirements.txt"
    
    echo "🔨 Building process_word_document..."
    
    # Ensure pandoc layer exists
    if [[ ! -f "$TEMP_DIR/pandoc_layer.zip" ]]; then
        echo "📦 Pandoc layer required, building..."
        build_pandoc_layer
    fi
    
    # Check if requirements.txt exists for this function
    if [[ -f "$requirements_file" ]]; then
        # Create temporary package directory for functions with dependencies
        local package_dir="$TEMP_DIR/package_${func_name}"
        mkdir -p "$package_dir"
        
        # Install dependencies
        install_dependencies "$func_name" "$package_dir"
        
        # Copy function file
        cp "$LAMBDA_DIR/process_word_document.py" "$package_dir/"
        
        # Create zip file
        cd "$package_dir"
        zip -r "$zip_file" . -q
        cd - > /dev/null
        
        # Cleanup package directory
        rm -rf "$package_dir"
    else
        # Simple zip for function without dependencies
        zip -j "$zip_file" "$LAMBDA_DIR/process_word_document.py" >/dev/null 2>&1
    fi
    
    echo "✅ process_word_document built and packaged"
}

# Build OpenSearch layer with correct Lambda layer structure
build_opensearch_layer() {
    local layer_zip="$LAMBDA_DIR/opensearch_layer.zip"
    echo "🔨 Building OpenSearch layer..."
    echo "📦 Adding opensearchpy and requests_aws4auth..."
    
    # Create temporary layer structure
    local layer_dir="$TEMP_DIR/opensearch_layer_build"
    mkdir -p "$layer_dir/python"
    
    # Copy dependencies to python/ directory for Lambda layer
    if [[ -d "$DEPENDENCIES_DIR/opensearchpy" ]] && [[ -d "$DEPENDENCIES_DIR/requests_aws4auth" ]]; then
        cp -r "$DEPENDENCIES_DIR/opensearchpy/" "$layer_dir/python/"
        cp -r "$DEPENDENCIES_DIR/requests_aws4auth/" "$layer_dir/python/"
    else
        error "Dependencies not found in $DEPENDENCIES_DIR"
    fi
    
    # Create layer zip with correct structure
    cd "$layer_dir" || error "Failed to cd to $layer_dir"
    zip -r "$layer_zip" . >/dev/null 2>&1
    cd "$PROJECT_ROOT" || error "Failed to cd to $PROJECT_ROOT"
    
    # Cleanup
    rm -rf "$layer_dir"
    
    echo "✅ OpenSearch layer built and packaged with correct Lambda structure"
}

# Deploy layer to AWS
deploy_layer() {
    local layer_name=$1
    local layer_zip=""
    local aws_layer_name=""
    
    case $layer_name in
        "opensearch")
            layer_zip="$LAMBDA_DIR/opensearch_layer.zip"
            aws_layer_name="risk-agent-opensearch-layer"
            ;;
        "pandoc")
            layer_zip="$TEMP_DIR/pandoc_layer.zip"
            aws_layer_name="risk-agent-pandoc-layer"
            ;;
        "inspector")
            layer_zip="$LAMBDA_DIR/layers/inspector_layer.zip"
            aws_layer_name="risk-agent-inspector-layer"
            ;;
        *)
            error "Unknown layer: $layer_name"
            ;;
    esac
    
    if [[ ! -f "$layer_zip" ]]; then
        error "Layer zip not found: $layer_zip"
    fi
    
    echo "🚀 Deploying $layer_name layer to AWS..."
    if aws_cmd "Layer $layer_name deployment" \
        aws lambda publish-layer-version \
        --layer-name "$aws_layer_name" \
        --zip-file "fileb://$layer_zip" \
        --compatible-runtimes python3.9 python3.11 \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION"; then
        # aws_cmd already shows success message
        true
    else
        FAILED_DEPLOYMENTS+=("layer: $layer_name")
        warn "Continuing with remaining layers"
    fi
}

# Deploy Lambda function
deploy_function() {
    local func_name=$1
    local zip_file="$TEMP_DIR/${func_name}.zip"
    
    if [[ ! -f "$zip_file" ]]; then
        error "Function zip not found: $zip_file"
    fi
    
    # All AWS functions have risk-agent- prefix with underscores
    local aws_func_name="risk-agent-${func_name}"
    
    echo "🚀 Deploying $func_name to AWS (as $aws_func_name)..."
    
    # Check if function exists
    if aws lambda get-function --function-name "$aws_func_name" --profile "$AWS_PROFILE" --region "$AWS_REGION" >/dev/null 2>&1; then
        # Update existing function
        if aws_cmd "Function $func_name deployment" \
            aws lambda update-function-code \
            --function-name "$aws_func_name" \
            --zip-file "fileb://$zip_file" \
            --profile "$AWS_PROFILE" \
            --region "$AWS_REGION"; then
            true  # Success already handled by aws_cmd
        else
            FAILED_DEPLOYMENTS+=("function: $func_name")
            warn "Continuing with remaining deployments"
        fi
    else
        echo "⚠️ Function $aws_func_name not found in AWS - skipping"
        return 0
    fi
}

# Upload system prompts to S3
upload_system_prompts() {
    echo "📤 Uploading system prompts to S3..."
    
    # Get the S3 bucket name from terraform output
    local bucket_name
    bucket_name=$(aws s3api list-buckets --query "Buckets[?contains(Name, 'risk-agent-app-data')].Name" --output text --profile "$AWS_PROFILE" 2>/dev/null | head -1)
    
    if [[ -z "$bucket_name" ]]; then
        error "Could not find risk-agent-app-data S3 bucket"
    fi
    
    echo "📦 Using S3 bucket: $bucket_name"
    
    # Upload each system prompt file
    local upload_failed=0
    for prompt_file in "${SYSTEM_PROMPTS[@]}"; do
        local src_file="$PROJECT_ROOT/system_prompts/$prompt_file"
        local s3_key="system prompts/$prompt_file"  # Note: space in path as expected by Lambda
        
        if [[ -f "$src_file" ]]; then
            echo "📤 Uploading $prompt_file..."
            if aws s3 cp "$src_file" "s3://$bucket_name/$s3_key" --profile "$AWS_PROFILE" --region "$AWS_REGION" >/dev/null 2>&1; then
                echo "✅ $prompt_file uploaded successfully"
            else
                warn "Failed to upload $prompt_file"
                upload_failed=$((upload_failed + 1))
            fi
        else
            warn "System prompt file not found: $src_file"
            upload_failed=$((upload_failed + 1))
        fi
    done
    
    if [[ $upload_failed -eq 0 ]]; then
        echo "✅ System prompts upload completed"
    else
        FAILED_DEPLOYMENTS+=("system-prompts: $upload_failed files failed")
        warn "System prompts upload completed with $upload_failed failures"
    fi
}

# Deploy admin function (uses lambda_functions.zip)
deploy_admin_function() {
    local func_name=$1
    local zip_file="$TEMP_DIR/lambda_functions.zip"
    
    if [[ ! -f "$zip_file" ]]; then
        error "Admin functions zip not found: $zip_file"
    fi
    
    # Map to AWS function names
    local aws_func_name="risk-agent-${func_name//_/-}"
    
    echo "🚀 Deploying $func_name to AWS (as $aws_func_name)..."
    
    # Check if function exists
    if aws lambda get-function --function-name "$aws_func_name" --profile "$AWS_PROFILE" --region "$AWS_REGION" >/dev/null 2>&1; then
        # Update existing function
        aws lambda update-function-code \
            --function-name "$aws_func_name" \
            --zip-file "fileb://$zip_file" \
            --profile "$AWS_PROFILE" \
            --region "$AWS_REGION" >/dev/null
        echo "✅ $func_name deployed successfully to $aws_func_name"
    else
        echo "⚠️ Function $aws_func_name not found in AWS - skipping"
        return 0
    fi
}

# Build all functions
build_all() {
    echo "🔨 Building all Lambda functions and layers..."
    echo ""
    
    # Build layers first
    echo "📦 Building layers..."
    for layer in "${LAYERS[@]}"; do
        case $layer in
            "opensearch") build_opensearch_layer ;;
            "pandoc") build_pandoc_layer ;;
        esac
    done
    echo ""
    
    # Build consolidated functions first
    echo "🔨 Building consolidated functions..."
    for func in "${CONSOLIDATED_FUNCTIONS[@]}"; do
        build_consolidated_function "$func"
    done
    echo ""
    
    # Build simple functions
    echo "🔨 Building simple functions..."
    for func in "${SIMPLE_FUNCTIONS[@]}"; do
        build_simple_function "$func"
    done
    echo ""
    
    # Build complex functions
    echo "🔨 Building complex functions..."
    build_process_word_document
    echo ""

    
    echo "🎉 All functions and layers built successfully!"
}

# Progress helper for Deploy all
progress() {
    CURRENT_ITEM=$((CURRENT_ITEM + 1))
    local elapsed=$(($(date +%s) - START_TIME))
    echo "[$CURRENT_ITEM/$TOTAL_ITEMS] $1 (${elapsed}s)"
}



# Deploy all functions
deploy_all() {
    echo "🚀 Deploying all Lambda functions and layers to AWS..."
    echo ""
    
    TOTAL_ITEMS=$((${#LAYERS[@]} + ${#CONSOLIDATED_FUNCTIONS[@]} + ${#SIMPLE_FUNCTIONS[@]} + ${#COMPLEX_FUNCTIONS[@]} + 1))
    CURRENT_ITEM=0
    START_TIME=$(date +%s)
    FAILED_DEPLOYMENTS=()  # Reset failure tracking

    # Upload system prompts first
    progress "Uploading system prompts"
    upload_system_prompts
    echo ""
    
    # Deploy layers first
    echo "📦 Deploying layers..."
    for layer in "${LAYERS[@]}"; do
        progress "Deploying layer: $layer"
        deploy_layer "$layer"
    done
    echo ""
    
    # Deploy consolidated functions first
    echo "🚀 Deploying consolidated functions..."
    for func in "${CONSOLIDATED_FUNCTIONS[@]}"; do
        progress "Deploying function: $func"
        deploy_function "$func"
    done
    
    # Deploy all functions
    echo "🚀 Deploying simple functions..."
    for func in "${SIMPLE_FUNCTIONS[@]}"; do
        progress "Deploying function: $func"
        deploy_function "$func"
    done
    
    for func in "${COMPLEX_FUNCTIONS[@]}"; do
        progress "Deploying function: $func"
        deploy_function "$func"
    done

    local total_time=$(($(date +%s) - START_TIME))
    
    if [[ ${#FAILED_DEPLOYMENTS[@]} -eq 0 ]]; then
        echo "🎉 All functions and layers deployed successfully in ${total_time}s!"
    else
        echo "⚠️ Deployment completed with ${#FAILED_DEPLOYMENTS[@]} failures in ${total_time}s!"
        echo ""
        echo "Failed deployments:"
        printf '  • %s\n' "${FAILED_DEPLOYMENTS[@]}"
        echo ""
        echo "To retry failed deployments:"
        for failed in "${FAILED_DEPLOYMENTS[@]}"; do
            local item_name=$(echo "$failed" | cut -d':' -f2 | xargs)
            echo "  ./deploy_lambdas_unified.sh $item_name deploy"
        done
    fi
}

# Build and deploy specific item
build_deploy_item() {
    local item=$1
    local action=$2
    
    # Check if it's a layer
    if [[ " ${LAYERS[@]} " =~ " ${item} " ]]; then
        if [[ "$action" == "build" || "$action" == "both" ]]; then
            case $item in
                "opensearch") build_opensearch_layer ;;
                "pandoc") build_pandoc_layer ;;
            esac
        fi
        if [[ "$action" == "deploy" || "$action" == "both" ]]; then
            deploy_layer "$item"
        fi
        return 0
    fi
    
    # Check if it's a consolidated function
    if [[ " ${CONSOLIDATED_FUNCTIONS[@]} " =~ " ${item} " ]]; then
        if [[ "$action" == "build" || "$action" == "both" ]]; then
            build_consolidated_function "$item"
        fi
        if [[ "$action" == "deploy" || "$action" == "both" ]]; then
            deploy_function "$item"
        fi
        return 0
    fi
    
    # Check if it's a function
    if [[ " ${SIMPLE_FUNCTIONS[@]} " =~ " ${item} " ]]; then
        if [[ "$action" == "build" || "$action" == "both" ]]; then
            build_simple_function "$item"
        fi
        if [[ "$action" == "deploy" || "$action" == "both" ]]; then
            deploy_function "$item"
        fi
        return 0
    fi
    
    # Check if it's a complex function
    if [[ " ${COMPLEX_FUNCTIONS[@]} " =~ " ${item} " ]]; then
        if [[ "$action" == "build" || "$action" == "both" ]]; then
            case $item in
                "process_word_document") build_process_word_document ;;
            esac
        fi
        if [[ "$action" == "deploy" || "$action" == "both" ]]; then
            deploy_function "$item"
        fi
        return 0
    fi
    
    # Check if it's an admin function
    if [[ " ${ADMIN_FUNCTIONS[@]} " =~ " ${item} " ]]; then
        if [[ "$action" == "build" || "$action" == "both" ]]; then
            build_admin_functions
        fi
        if [[ "$action" == "deploy" || "$action" == "both" ]]; then
            deploy_admin_function "$item"
        fi
        return 0
    fi
    
    error "Unknown function or layer: $item"
}

# Show help function
show_help() {
    cat << EOF
🚀 Unified Lambda Deployment Script

DESCRIPTION:
    Handles all Lambda functions, layers, build, and deployment for the Risk Agent project.
    Supports building ZIP packages locally and deploying to AWS Lambda functions.

USAGE:
    ./deploy_lambdas_unified.sh [TARGET] [ACTION] [AWS_PROFILE]
    ./deploy_lambdas_unified.sh [--help|-h]

PARAMETERS:
    TARGET      What to build/deploy (default: help - shows this help)
                • all           - All functions and layers
                • list          - Show available functions and layers
                • prompts       - Upload system prompts to S3
                • <function>    - Specific function name
                • <layer>       - Specific layer name

    ACTION      What action to perform (default: both)
                • build         - Build packages locally only
                • deploy        - Deploy to AWS only (requires existing functions)
                • both          - Build and deploy

    AWS_PROFILE AWS profile to use (default: \$AWS_PROFILE environment variable)
                • <profile>     - Specific AWS profile name

EXAMPLES:
    # Show help (default behavior)
    ./deploy_lambdas_unified.sh

    # Build and deploy everything
    ./deploy_lambdas_unified.sh all

    # Build all packages only
    ./deploy_lambdas_unified.sh all build

    # Deploy all to AWS only (functions must exist) and sets a aws-profile to override AWS_PROFILE variable
    ./deploy_lambdas_unified.sh all deploy my-aws-profile

    # Build and deploy specific function
    ./deploy_lambdas_unified.sh document_manager both

    # Deploy specific layer
    ./deploy_lambdas_unified.sh opensearch deploy

    # Upload system prompts only
    ./deploy_lambdas_unified.sh prompts

    # List available functions and layers
    ./deploy_lambdas_unified.sh list

AVAILABLE TARGETS:
    Consolidated Functions:
$(printf '        • %s\n' "${CONSOLIDATED_FUNCTIONS[@]}")

    Simple Functions:
$(printf '        • %s\n' "${SIMPLE_FUNCTIONS[@]}")

    Complex Functions:
$(printf '        • %s\n' "${COMPLEX_FUNCTIONS[@]}")

    Layers:
$(printf '        • %s\n' "${LAYERS[@]}")

DEPLOYMENT WORKFLOW:
    First-time deployment:
    1. ./deploy_lambdas_unified.sh all build      # Build packages
    2. terraform apply                            # Create infrastructure
    3. ./deploy_lambdas_unified.sh all deploy     # Deploy code

    Code updates:
    ./deploy_lambdas_unified.sh all both          # Build and deploy

REQUIREMENTS:
    • AWS CLI configured with appropriate permissions
    • Python 3.11+ with pip3
    • Docker Desktop (for some dependencies)
    • Terraform (for infrastructure provisioning)

NOTES:
    • Functions must exist in AWS before deploying (created by Terraform)
    • Script will skip deployment if functions don't exist
    • All AWS function names have 'risk-agent-' prefix
    • Layers are deployed with version updates
    • System prompts are uploaded to S3 bucket

EOF
}

# Check for help flag
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

# Main execution
TARGET=${1:-help}
ACTION=${2:-both}
AWS_PROFILE=${3:-${AWS_PROFILE}}

log "Using AWS Profile: $AWS_PROFILE"

case $TARGET in
    "help")
        show_help
        exit 0
        ;;
    "all")
        if [[ "$ACTION" == "build" || "$ACTION" == "both" ]]; then
            build_all
        fi
        if [[ "$ACTION" == "deploy" || "$ACTION" == "both" ]]; then
            deploy_all
        fi
        ;;
    "list")
        echo "Available consolidated functions:"
        printf '%s\n' "${CONSOLIDATED_FUNCTIONS[@]}"
        echo ""
        echo "Available simple functions:"
        printf '%s\n' "${SIMPLE_FUNCTIONS[@]}"
        echo ""
        echo "Available complex functions:"
        printf '%s\n' "${COMPLEX_FUNCTIONS[@]}"
        echo ""
        echo "Available admin functions:"
        printf '%s\n' "${ADMIN_FUNCTIONS[@]}"
        echo ""
        echo "Available layers:"
        printf '%s\n' "${LAYERS[@]}"
        echo ""
        echo "Available system prompts:"
        printf '%s\n' "${SYSTEM_PROMPTS[@]}"
        ;;
    "prompts")
        upload_system_prompts
        ;;
    *)
        build_deploy_item "$TARGET" "$ACTION"
        ;;
esac

log "✨ Lambda deployment complete"
