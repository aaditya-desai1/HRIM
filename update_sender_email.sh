#!/bin/bash
# Script to update the SENDER_EMAIL environment variable for Lambda functions

# Default values
SENDER_EMAIL="desaiaditya2710@gmail.com"
AWS_REGION="us-east-1"
LOCAL_ONLY=false

# Check dependencies
check_dependencies() {
  local missing_deps=false

  if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    echo "Installation guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    missing_deps=true
  fi

  if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install it first."
    echo "Installation guide: https://stedolan.github.io/jq/download/"
    missing_deps=true
  fi

  if [ "$missing_deps" = true ]; then
    exit 1
  fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --sender-email)
      SENDER_EMAIL="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --local-only)
      LOCAL_ONLY=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --sender-email EMAIL   Sender email address (default: $SENDER_EMAIL)"
      echo "  --region REGION        AWS region (default: from AWS config)"
      echo "  --local-only           Update only local environment, skip Lambda functions"
      echo "  --help                 Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Update local environment
echo "Setting local environment variable SENDER_EMAIL=$SENDER_EMAIL"
export SENDER_EMAIL=$SENDER_EMAIL
echo "export SENDER_EMAIL=$SENDER_EMAIL" >> ~/.bashrc
echo "Local environment variable set. Run 'source ~/.bashrc' to apply in current shell."

# Exit if local-only flag is set
if [ "$LOCAL_ONLY" = true ]; then
  echo "✅ Local environment updated. Skipping Lambda functions."
  exit 0
fi

# Check for required dependencies for AWS operations
check_dependencies

# Build region parameter
REGION_PARAM=""
if [ -n "$AWS_REGION" ]; then
  REGION_PARAM="--region $AWS_REGION"
  echo "Using AWS region: $AWS_REGION"
else
  # Try to get default region from AWS configuration
  DEFAULT_REGION=$(aws configure get region 2>/dev/null)
  if [ -n "$DEFAULT_REGION" ]; then
    REGION_PARAM="--region $DEFAULT_REGION"
    echo "Using default AWS region from config: $DEFAULT_REGION"
  else
    echo "No AWS region specified and no default region found in AWS config."
    echo "Please specify a region with --region or configure a default region with 'aws configure'."
    exit 1
  fi
fi

# Functions that might use SENDER_EMAIL
FUNCTIONS=("hrim-send-email" "hrim-utils")

echo "Setting SENDER_EMAIL to $SENDER_EMAIL for Lambda functions..."

function_updated=false

for FUNCTION_NAME in "${FUNCTIONS[@]}"; do
  echo "Updating environment variables for $FUNCTION_NAME..."

  # Get current environment variables
  ENV_VARS=$(aws lambda get-function-configuration \
    --function-name $FUNCTION_NAME \
    $REGION_PARAM \
    --query "Environment.Variables" \
    --output json 2>/dev/null)

  # Check if the function exists
  if [ $? -ne 0 ]; then
    echo "Warning: Function $FUNCTION_NAME not found, skipping..."
    continue
  fi

  function_updated=true

  # Check if the function has environment variables
  if [ "$ENV_VARS" == "null" ]; then
    echo "Function $FUNCTION_NAME has no environment variables, creating new ones..."
    ENV_VARS="{}"
  fi

  # Create JSON for the update
  TMP_FILE=$(mktemp)
  echo "{
    \"Variables\": $(echo $ENV_VARS | jq ". + {\"SENDER_EMAIL\": \"$SENDER_EMAIL\"}")
  }" > $TMP_FILE

  # Update Lambda function configuration
  aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    $REGION_PARAM \
    --environment file://$TMP_FILE

  if [ $? -eq 0 ]; then
    echo "Successfully updated Lambda environment variables for $FUNCTION_NAME."
  else
    echo "Error: Failed to update Lambda environment variables for $FUNCTION_NAME."
    echo "Please check that you have the lambda:UpdateFunctionConfiguration permission."
    rm $TMP_FILE
    exit 1
  fi

  rm $TMP_FILE
done

if [ "$function_updated" = false ]; then
  echo "⚠️ No Lambda functions were updated. They may not exist yet or you may need to deploy first."
else
  echo "✅ Lambda functions updated successfully."
fi

echo "✅ Done! SENDER_EMAIL environment variable updated to $SENDER_EMAIL."
echo "Email will now be sent from this address for all Lambda functions."
echo "Note: Make sure this email is verified in Amazon SES if your account is in sandbox mode." 