#!/bin/bash

# This script uploads the prompt.txt file to the S3 bucket
# Usage: ./upload_prompt_template.sh [bucket-name]

set -e

# Default bucket name (can be overridden by first argument)
BUCKET_NAME=${1:-hrim-input-data}

# Path to the prompt template file
PROMPT_FILE="test-data/prompt.txt"

# Check if the prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Error: Prompt file not found at $PROMPT_FILE"
    exit 1
fi

# S3 destination key
DEST_KEY="templates/prompt.txt"

echo "Uploading prompt template to s3://$BUCKET_NAME/$DEST_KEY..."
aws s3 cp "$PROMPT_FILE" "s3://$BUCKET_NAME/$DEST_KEY"

echo "Setting content type metadata..."
aws s3api copy-object \
    --copy-source "$BUCKET_NAME/$DEST_KEY" \
    --bucket "$BUCKET_NAME" \
    --key "$DEST_KEY" \
    --content-type "text/plain" \
    --metadata-directive "REPLACE"

echo "Prompt template uploaded successfully."
echo "The prompt template is now available at: s3://$BUCKET_NAME/$DEST_KEY"
echo ""
echo "Make sure to set the PROMPT_FILE_KEY environment variable for the format_prompt Lambda:"
echo "PROMPT_FILE_KEY=templates/prompt.txt" 