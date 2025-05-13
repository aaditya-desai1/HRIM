"""
Call Gemini API lambda function.

This function calls the Google Gemini API with the formatted prompt
to generate a personalized wellness plan.
"""

import json
import os
import logging
import sys
import requests
import boto3
from typing import Dict, Any, Optional
import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Gemini API configuration
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_K = 40
DEFAULT_TOP_P = 0.95

# Get environment variables
JOB_TABLE_NAME = os.environ.get('JOB_TABLE_NAME', 'hrim-jobs')
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'hrim-input-data')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'hrim-output-data')
SECRETS_NAME = os.environ.get('SECRETS_NAME', 'hrim-secrets')

# Define job status constants
class JobStatus:
    CREATED = 'CREATED'
    FETCHING_DATA = 'FETCHING_DATA'
    FORMATTING_PROMPT = 'FORMATTING_PROMPT'
    CALLING_AI = 'CALLING_AI'
    GENERATING_PDF = 'GENERATING_PDF'
    UPLOADING_PDF = 'UPLOADING_PDF'
    SENDING_EMAIL = 'SENDING_EMAIL'
    SENDING_WHATSAPP = 'SENDING_WHATSAPP'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

def update_job_status(job_id: str, status: str, error: Optional[str] = None) -> None:
    """
    Update the status of a job in DynamoDB.
    
    Args:
        job_id: The job ID
        status: The new status
        error: Optional error message
    """
    try:
        # Initialize the DynamoDB resource
        dynamodb = boto3.resource('dynamodb')
        
        # Update job status in DynamoDB
        table = dynamodb.Table(JOB_TABLE_NAME)
        
        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_attribute_names = {
            '#status': 'status'
        }
        expression_attribute_values = {
            ':status': status,
            ':updated_at': datetime.datetime.now().isoformat()
        }
        
        if error:
            update_expression += ", error_message = :error_message"
            expression_attribute_values[':error_message'] = error
        
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(f"Updated job status: {job_id} -> {status}")
    except Exception as e:
        logger.error(f"Error updating job status: {str(e)}")
        # Don't raise, as this might be a non-critical error

def write_to_s3(bucket: str, key: str, data: str, content_type: str = 'application/json') -> None:
    """
    Write data to S3.
    
    Args:
        bucket: The S3 bucket name
        key: The S3 object key
        data: The data to write
        content_type: The content type
    """
    try:
        # Initialize the S3 client
        s3_client = boto3.client('s3')
        
        s3_client.put_object(
            Body=data,
            Bucket=bucket,
            Key=key,
            ContentType=content_type
        )
        logger.info(f"Wrote data to S3: {bucket}/{key}")
    except Exception as e:
        logger.error(f"Error writing to S3: {str(e)}")
        raise

def get_secret_value(secret_name: str) -> Dict[str, Any]:
    """
    Get a secret value from AWS Secrets Manager.
    
    Args:
        secret_name: Name of the secret
        
    Returns:
        Secret value as a dictionary
    """
    try:
        # Create a Secrets Manager client
        client = boto3.client('secretsmanager')
        
        # Get the secret value
        response = client.get_secret_value(SecretId=secret_name)
        
        # Parse the secret value (JSON string)
        if 'SecretString' in response:
            secret = json.loads(response['SecretString'])
            return secret
        else:
            logger.warning(f"Secret {secret_name} does not contain SecretString")
            return {}
    except Exception as e:
        logger.error(f"Error getting secret {secret_name}: {str(e)}")
        return {}

def call_gemini_api(prompt: str, model_name: Optional[str] = None) -> str:
    """
    Call the Gemini API with the formatted prompt using direct REST API calls.
    
    Args:
        prompt: The formatted prompt
        model_name: The model name to use
        
    Returns:
        Generated response from Gemini
    """
    try:
        # Use default model if none specified
        if not model_name:
            model_name = DEFAULT_GEMINI_MODEL
        
        logger.info(f"Calling Gemini API with model: {model_name}")
        
        # Get API key from environment variables
        api_key = os.environ.get('GEMINI_API_KEY')
        
        # If not in environment variables, try getting from Secrets Manager
        if not api_key:
            logger.info("GEMINI_API_KEY not found in environment variables, trying Secrets Manager")
            secrets = get_secret_value(SECRETS_NAME)
            api_key = secrets.get('GEMINI_API_KEY')
        
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables or Secrets Manager")
            raise ValueError("GEMINI_API_KEY not found in environment variables or Secrets Manager")
        
        # API endpoint
        url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
        
        # Request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": DEFAULT_TEMPERATURE,
                "topK": DEFAULT_TOP_K,
                "topP": DEFAULT_TOP_P,
                "maxOutputTokens": DEFAULT_MAX_OUTPUT_TOKENS
            }
        }
        
        # Make the API call
        logger.info("Sending request to Gemini API")
        response = requests.post(url, json=payload)
        
        # Check for successful response
        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            raise Exception(f"Gemini API returned status code {response.status_code}: {response.text}")
        
        # Parse the response
        response_json = response.json()
        logger.info("Received response from Gemini API")
        
        # Extract the text from the response
        try:
            text = response_json['candidates'][0]['content']['parts'][0]['text']
            return text
        except (KeyError, IndexError) as e:
            logger.error(f"Error extracting text from Gemini response: {str(e)}")
            logger.error(f"Response: {json.dumps(response_json)}")
            raise Exception(f"Could not extract text from Gemini response: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}", exc_info=True)
        raise

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict containing job_id and prompt
        context: Lambda context
        
    Returns:
        Dict containing job ID, response, and status
    """
    try:
        # Parse the event
        if 'body' in event:
            # If coming from API Gateway
            body = json.loads(event['body'])
            job_id = body.get('job_id')
            prompt = body.get('prompt')
            client_data = body.get('client_data')
        else:
            # If coming from direct Lambda invocation
            job_id = event.get('job_id')
            prompt = event.get('prompt')
            client_data = event.get('client_data')
        
        logger.info(f"Processing Gemini API call for job: {job_id}")
        
        if not job_id or not prompt:
            logger.error("Missing required parameters: job_id or prompt")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Update job status
        update_job_status(job_id, JobStatus.CALLING_AI)
        
        # Call Gemini API
        response = call_gemini_api(prompt)
        
        # Store the response in S3
        response_key = f"jobs/{job_id}/gemini_response.md"
        write_to_s3(OUTPUT_BUCKET, response_key, response, 'text/markdown')
        
        logger.info(f"Stored Gemini API response for job: {job_id}")
        
        # Prepare result for next step
        result = {
            'job_id': job_id,
            'prompt': prompt,
            'response': response,
            'response_key': response_key,
            'client_data': client_data,
            'status': JobStatus.GENERATING_PDF
        }
        
        # Update job status to indicate we're moving to generate PDF
        update_job_status(job_id, JobStatus.GENERATING_PDF)
        
        logger.info(f"Job {job_id} proceeding to generate_pdf")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    
    except Exception as e:
        # Handle errors
        error_message = f"Error in call_gemini function: {str(e)}"
        logger.error(error_message, exc_info=True)
        
        # Update job status to FAILED if job_id is available
        if 'job_id' in locals() and job_id:
            update_job_status(job_id, JobStatus.FAILED, error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        } 