#!/bin/bash
# Simplified deployment script for HRIM

set -e

# Configurations
PYTHON_VERSION="python3"
VENV_DIR=".venv"
OUTPUT_DIR="build"
LAYER_DIR="${OUTPUT_DIR}/layer"
LAYER_PYTHON_DIR="${LAYER_DIR}/python"
LAMBDA_DIR="src/lambda"
TERRAFORM_DIR="terraform"

echo "===== HRIM Simplified Deployment Script ====="

# Check if required tools are available
echo "Checking requirements..."

if ! command -v ${PYTHON_VERSION} &> /dev/null; then
    echo "Error: ${PYTHON_VERSION} is not installed."
    exit 1
fi

# Check Python version is at least 3.8
PY_VERSION=$(${PYTHON_VERSION} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MAJOR" -eq 3 -a "$PY_MINOR" -lt 8 ]; then
    echo "Error: Python version must be at least 3.8 (found $PY_VERSION)"
    exit 1
fi

if ! command -v zip &> /dev/null; then
    echo "Error: zip is not installed."
    exit 1
fi

echo "Requirements check passed. Using Python $PY_VERSION."

# Set up virtual environment
echo "Setting up virtual environment..."

# Always start with a fresh venv
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment..."
    rm -rf ${VENV_DIR}
fi

echo "Creating new virtual environment..."
${PYTHON_VERSION} -m venv ${VENV_DIR}

# Verify the venv was created properly
if [ ! -f "${VENV_DIR}/bin/python" ]; then
    echo "Error: Failed to create virtual environment."
    exit 1
fi

echo "Virtual environment created at ${VENV_DIR}"

# Get the path to the python executable in the venv
VENV_PYTHON="${VENV_DIR}/bin/python"

# Upgrade pip and install dependencies
echo "Installing dependencies..."
${VENV_PYTHON} -m pip install --upgrade pip
${VENV_PYTHON} -m pip install -r requirements.txt

echo "Virtual environment set up successfully."

# Clean build directory
echo "Cleaning build directory..."
rm -rf ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR}
mkdir -p ${LAYER_PYTHON_DIR}
echo "Build directory cleaned."

# Create layer with dependencies
echo "Creating Lambda layer..."
${VENV_PYTHON} -m pip install -r requirements.txt --target ${LAYER_PYTHON_DIR}

# Create the layer zip file
cd ${LAYER_DIR}
zip -r ../lambda_layer.zip .
cd ../..
echo "Lambda layer created at ${OUTPUT_DIR}/lambda_layer.zip"

# Create a shared utils module
echo "Preparing shared utils..."
mkdir -p ${OUTPUT_DIR}/utils
cp ${LAMBDA_DIR}/utils.py ${OUTPUT_DIR}/utils/
echo "Shared utils prepared."

# Package Lambda functions
echo "Packaging Lambda functions..."

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
    echo "Packaging $func..."
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
echo "All Lambda functions packaged successfully."

# Deploy the serverless application using Terraform
if command -v terraform &> /dev/null; then
    echo "Deploying with Terraform..."
    
    cd ${TERRAFORM_DIR}
    
    terraform init
    terraform validate
    
    # Ask for confirmation before applying
    echo "Do you want to apply the Terraform configuration? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        terraform apply
        echo "Terraform deployment completed."
    else
        echo "Terraform deployment skipped."
    fi
    
    cd ..
else
    echo "Terraform not installed, deployment skipped."
fi

echo "===== Deployment completed =====" 