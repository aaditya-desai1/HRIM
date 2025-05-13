#!/bin/bash
# Deployment script for HRIM

set -e

# Configurations
PYTHON_VERSION="python3"  # Use system python3
VENV_DIR=".venv"
OUTPUT_DIR="build"
LAYER_DIR="${OUTPUT_DIR}/layer"
LAYER_PYTHON_DIR="${LAYER_DIR}/python"
LAMBDA_DIR="src/lambda"
TERRAFORM_DIR="terraform"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if required tools are available
check_requirements() {
    echo -e "${YELLOW}Checking requirements...${NC}"
    
    if ! command -v ${PYTHON_VERSION} &> /dev/null; then
        echo -e "${RED}Error: ${PYTHON_VERSION} is not installed.${NC}"
        exit 1
    fi
    
    # Check Python version is at least 3.8
    PY_VERSION=$(${PYTHON_VERSION} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)
    
    if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MAJOR" -eq 3 -a "$PY_MINOR" -lt 8 ]; then
        echo -e "${RED}Error: Python version must be at least 3.8 (found $PY_VERSION)${NC}"
        exit 1
    fi
    
    if ! command -v zip &> /dev/null; then
        echo -e "${RED}Error: zip is not installed.${NC}"
        exit 1
    fi
    
    if ! command -v terraform &> /dev/null; then
        echo -e "${YELLOW}Warning: Terraform is not installed. Terraform steps will be skipped.${NC}"
    fi
    
    if ! command -v aws &> /dev/null; then
        echo -e "${YELLOW}Warning: AWS CLI is not installed. AWS operations will be skipped.${NC}"
    fi
    
    echo -e "${GREEN}Requirements check passed. Using Python $PY_VERSION.${NC}"
}

# Create virtual environment and return the path to the python executable
setup_venv() {
    echo -e "${YELLOW}Setting up virtual environment...${NC}"
    
    # Always start with a fresh venv
    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Removing existing virtual environment...${NC}"
        rm -rf ${VENV_DIR}
    fi
    
    echo -e "${YELLOW}Creating new virtual environment...${NC}"
    ${PYTHON_VERSION} -m venv ${VENV_DIR}
    
    # Verify the venv was created properly
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        echo -e "${RED}Error: Failed to create virtual environment.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Virtual environment created at ${VENV_DIR}${NC}"
    
    # Get the path to the python executable in the venv
    VENV_PYTHON="${VENV_DIR}/bin/python"
    
    # Upgrade pip and install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    ${VENV_PYTHON} -m pip install --upgrade pip
    ${VENV_PYTHON} -m pip install -r requirements.txt
    
    echo -e "${GREEN}Virtual environment set up successfully.${NC}"
    
    # Return the path to the python executable
    echo ${VENV_PYTHON}
}

# Clean build directory
clean_build() {
    echo -e "${YELLOW}Cleaning build directory...${NC}"
    
    rm -rf ${OUTPUT_DIR}
    mkdir -p ${OUTPUT_DIR}
    mkdir -p ${LAYER_PYTHON_DIR}
    
    echo -e "${GREEN}Build directory cleaned.${NC}"
}

# Create layer with dependencies
create_layer() {
    VENV_PYTHON="$1"
    
    echo -e "${YELLOW}Creating Lambda layer...${NC}"
    
    # Install dependencies into the layer directory
    ${VENV_PYTHON} -m pip install -r requirements.txt --target ${LAYER_PYTHON_DIR}
    
    # Create the layer zip file
    cd ${LAYER_DIR}
    zip -r ../lambda_layer.zip .
    cd ../..
    
    echo -e "${GREEN}Lambda layer created at ${OUTPUT_DIR}/lambda_layer.zip${NC}"
}

# Create a shared utils module
prepare_shared_utils() {
    echo -e "${YELLOW}Preparing shared utils...${NC}"
    
    mkdir -p ${OUTPUT_DIR}/utils
    cp ${LAMBDA_DIR}/utils.py ${OUTPUT_DIR}/utils/
    
    echo -e "${GREEN}Shared utils prepared.${NC}"
}

# Package Lambda functions
package_lambdas() {
    echo -e "${YELLOW}Packaging Lambda functions...${NC}"
    
    # List of Lambda functions to package
    LAMBDA_FUNCTIONS=(
        "trigger_processor"
        "fetch_data"
        "format_prompt"
        "call_gemini"
        "generate_pdf"
        "upload_pdf"
        "send_email"
        "complete_job"
        "form_submission"
    )
    
    # Create temp directory for packaging
    mkdir -p temp
    
    # Copy utils.py to temp directory
    cp src/lambda/utils.py temp/
    
    # Loop through all Lambda functions
    for func in "${LAMBDA_FUNCTIONS[@]}"; do
        echo -e "${GREEN}Packaging $func...${NC}"
        mkdir -p "deployment/$func"
        
        # Package Lambda function
        cd temp
        cp -R "../src/lambda/$func/"* .
        zip -r "../deployment/$func/lambda_function.zip" * -x "*.git*" "*.pytest_cache*" "__pycache__/*" "*.pyc" "tests/*" "*__pycache__*" > /dev/null
        cd ..
        
        # Create a symbolic link in the Lambda function directory for Terraform
        ln -sf "$(pwd)/deployment/$func/lambda_function.zip" "src/lambda/$func/lambda_function.zip"
        
        # Clean up temp directory
        rm -rf temp/*
    done
    
    rm -rf temp
    
    echo -e "${GREEN}All Lambda functions packaged successfully.${NC}"
}

# Deploy the serverless application using Terraform
deploy_terraform() {
    if command -v terraform &> /dev/null; then
        echo -e "${YELLOW}Deploying with Terraform...${NC}"
        
        cd ${TERRAFORM_DIR}
        
        terraform init
        terraform validate
        
        # Ask for confirmation before applying
        echo -e "${YELLOW}Do you want to apply the Terraform configuration? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            terraform apply
            echo -e "${GREEN}Terraform deployment completed.${NC}"
        else
            echo -e "${YELLOW}Terraform deployment skipped.${NC}"
        fi
        
        cd ..
    else
        echo -e "${YELLOW}Terraform not installed, deployment skipped.${NC}"
    fi
}

# Main function
main() {
    echo -e "${GREEN}===== HRIM Deployment Script =====${NC}"
    
    check_requirements
    
    # Create virtual environment and get the path to the python executable
    VENV_PYTHON=$(setup_venv)
    
    clean_build
    create_layer "${VENV_PYTHON}"
    prepare_shared_utils
    package_lambdas
    deploy_terraform
    
    echo "Terraform apply completed successfully."

    # Upload the prompt template to S3
    echo "Uploading prompt template to S3..."
    BUCKET_NAME=$(terraform -chdir=terraform output -raw input_bucket_name 2>/dev/null || echo "hrim-input-data")
    ./upload_prompt_template.sh "$BUCKET_NAME"

    # Try to get the region from Terraform
    AWS_REGION=$(terraform -chdir=terraform output -raw aws_region 2>/dev/null)
    if [ -n "$AWS_REGION" ]; then
        echo "Setting PROMPT_FILE_KEY environment variable automatically..."
        ./update_prompt_env_var.sh --region "$AWS_REGION"
        if [ $? -eq 0 ]; then
            echo "✅ Environment variable set successfully!"
        else
            echo "⚠️ Could not automatically set the environment variable."
            echo "Please set it manually as described below."
        fi
    else
        echo "⚠️ Could not automatically determine AWS region from Terraform."
        echo "Please set the environment variable manually as described below."
    fi

    echo ""
    echo "IMPORTANT: Make sure the format_prompt Lambda function has the correct environment variable:"
    echo "PROMPT_FILE_KEY=templates/prompt.txt"
    echo ""
    echo "You can set this environment variable by:"
    echo "1. Running the update_prompt_env_var.sh script with your AWS region:"
    echo "   ./update_prompt_env_var.sh --region YOUR_AWS_REGION"
    echo "2. Or manually in the AWS Lambda console: https://console.aws.amazon.com/lambda"
    echo ""

    echo "Deployment completed successfully!"
}

# Execute main function
main 