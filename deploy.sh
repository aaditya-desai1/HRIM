#!/bin/bash

# Health & Wellness Report Implementation Manager (HRIM) Deployment Script
# -----------------------------------------------------------------------

echo "HRIM Deployment Script"
echo "======================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first:"
    echo "pip install awscli"
    echo "aws configure"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "Terraform is not installed. Please install it first."
    exit 1
fi

# Function to create necessary directories if they don't exist
create_dirs() {
    echo "Creating necessary directories..."
    mkdir -p src/lambda/{trigger_processor,fetch_data,format_prompt,call_openai,generate_pdf,upload_pdf,send_email,send_whatsapp,complete_job,handle_error}
    mkdir -p terraform
    mkdir -p test-data
    echo "Done."
    echo ""
}

# Function to set up AWS Secrets Manager secrets
setup_secrets() {
    echo "Setting up AWS Secrets Manager secrets..."
    echo ""
    echo "For OpenAI API:"
    echo "---------------"
    read -p "Enter your OpenAI API key: " openai_api_key
    
    # Create JSON file for the secret
    echo "{\"api_key\": \"$openai_api_key\"}" > openai_secret.json
    
    # Create the secret in AWS Secrets Manager
    aws secretsmanager create-secret --name HRIM/OpenAI/ApiKey --description "OpenAI API key for HRIM" --secret-string file://openai_secret.json
    
    echo ""
    echo "For WhatsApp API:"
    echo "----------------"
    read -p "Enter your WhatsApp API URL: " whatsapp_api_url
    read -p "Enter your WhatsApp access token: " whatsapp_access_token
    
    # Create JSON file for the secret
    echo "{\"api_url\": \"$whatsapp_api_url\", \"access_token\": \"$whatsapp_access_token\"}" > whatsapp_secret.json
    
    # Create the secret in AWS Secrets Manager
    aws secretsmanager create-secret --name HRIM/WhatsApp/ApiKey --description "WhatsApp API details for HRIM" --secret-string file://whatsapp_secret.json
    
    # Clean up temporary files
    rm -f openai_secret.json whatsapp_secret.json
    
    echo "Secrets created successfully."
    echo ""
}

# Function to deploy the infrastructure using Terraform
deploy_terraform() {
    echo "Deploying infrastructure using Terraform..."
    cd terraform
    
    echo "Initializing Terraform..."
    terraform init
    
    echo "Creating Terraform plan..."
    terraform plan -out=tfplan
    
    echo "Applying Terraform plan..."
    terraform apply tfplan
    
    cd ..
    echo "Infrastructure deployed successfully."
    echo ""
}

# Function to upload test data
upload_test_data() {
    echo "Uploading test data to S3..."
    
    # Get the input bucket name from Terraform output
    cd terraform
    input_bucket=$(terraform output -raw s3_buckets | grep input_bucket | cut -d'"' -f4)
    cd ..
    
    if [ -z "$input_bucket" ]; then
        echo "Could not get input bucket name from Terraform output."
        exit 1
    fi
    
    echo "Uploading sample form submission to s3://$input_bucket/forms/"
    aws s3 cp test-data/sample-form-submission.json s3://$input_bucket/forms/
    
    echo "Test data uploaded successfully."
    echo ""
}

# Main script

echo "What would you like to do?"
echo "1. Create directory structure"
echo "2. Set up AWS Secrets Manager secrets"
echo "3. Deploy infrastructure with Terraform"
echo "4. Upload test data to S3"
echo "5. Full deployment (all of the above)"
echo "6. Exit"

read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        create_dirs
        ;;
    2)
        setup_secrets
        ;;
    3)
        deploy_terraform
        ;;
    4)
        upload_test_data
        ;;
    5)
        create_dirs
        setup_secrets
        deploy_terraform
        upload_test_data
        
        echo "=================================================="
        echo "HRIM has been fully deployed!"
        echo "=================================================="
        echo ""
        echo "Next steps:"
        echo "1. Monitor the Step Functions execution in the AWS console"
        echo "2. Check the DynamoDB table for job status"
        echo "3. Look for the generated PDF in the output S3 bucket"
        echo "4. Verify email and WhatsApp delivery"
        echo ""
        ;;
    6)
        echo "Exiting."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo "Deployment script complete." 