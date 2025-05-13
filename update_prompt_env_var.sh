#!/bin/bash
# Script to update the PROMPT_FILE_KEY environment variable of the format_prompt Lambda function

# Default values
FUNCTION_NAME="hrim-format-prompt"
PROMPT_FILE_KEY="templates/prompt.txt"
AWS_REGION=""

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
    --function-name)
      FUNCTION_NAME="$2"
      shift 2
      ;;
    --prompt-key)
      PROMPT_FILE_KEY="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --function-name NAME   Lambda function name (default: $FUNCTION_NAME)"
      echo "  --prompt-key KEY       Prompt file key in S3 (default: $PROMPT_FILE_KEY)"
      echo "  --region REGION        AWS region (default: from AWS config)"
      echo "  --help                 Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check for required dependencies
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

echo "Updating Lambda environment variables for $FUNCTION_NAME..."

# Get current environment variables
ENV_VARS=$(aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  $REGION_PARAM \
  --query "Environment.Variables" \
  --output json)

if [ $? -ne 0 ]; then
  echo "Error: Failed to retrieve current environment variables."
  echo "Please check that:"
  echo "1. The Lambda function '$FUNCTION_NAME' exists in region $(echo $REGION_PARAM | cut -d' ' -f2)"
  echo "2. Your AWS credentials are configured correctly"
  echo "3. Your IAM user/role has permission to call lambda:GetFunctionConfiguration"
  exit 1
fi

# Update environment variables
echo "Setting PROMPT_FILE_KEY to $PROMPT_FILE_KEY"

# Create JSON for the update
TMP_FILE=$(mktemp)
echo "{
  \"Variables\": $(echo $ENV_VARS | jq ". + {\"PROMPT_FILE_KEY\": \"$PROMPT_FILE_KEY\"}")
}" > $TMP_FILE

# Update Lambda function configuration
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  $REGION_PARAM \
  --environment file://$TMP_FILE

if [ $? -eq 0 ]; then
  echo "Successfully updated Lambda environment variables."
else
  echo "Error: Failed to update Lambda environment variables."
  echo "Please check that you have the lambda:UpdateFunctionConfiguration permission."
  rm $TMP_FILE
  exit 1
fi

rm $TMP_FILE

echo "✅ Done! PROMPT_FILE_KEY environment variable updated."
echo "The format_prompt Lambda function will now use the prompt template at $PROMPT_FILE_KEY" 