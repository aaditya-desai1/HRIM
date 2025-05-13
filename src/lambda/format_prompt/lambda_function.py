"""
Format prompt lambda function.

This function prepares the client data for the Gemini API call by retrieving
the standard prompt template and preparing it alongside the client data.
"""

import json
import os
import logging
import sys
import boto3

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define S3 buckets or import from utils
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'hrim-input-data')
PROMPT_FILE_KEY = os.environ.get('PROMPT_FILE_KEY', 'templates/prompt.txt')

def get_standard_prompt():
    """
    Retrieve the standard prompt template from S3.
    
    Returns:
        The prompt text from the file
    """
    try:
        # Initialize the S3 client
        s3_client = boto3.client('s3')
        
        # Get the prompt file from S3
        response = s3_client.get_object(Bucket=INPUT_BUCKET, Key=PROMPT_FILE_KEY)
        prompt_text = response['Body'].read().decode('utf-8')
        logger.info(f"Successfully retrieved prompt template from {INPUT_BUCKET}/{PROMPT_FILE_KEY}")
        
        return prompt_text
    except Exception as e:
        logger.error(f"Error retrieving prompt template: {str(e)}")
        # If we can't retrieve the template, raise an exception (critical error)
        raise

def format_client_data(client_data):
    """
    Format client data into a structured JSON document for Gemini API.
    
    Args:
        client_data: Dict containing client data
        
    Returns:
        Formatted client data string in JSON format
    """
    # Just return the serialized client data
    return json.dumps(client_data, indent=2)

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict containing job_id and client_data
        context: Lambda context
        
    Returns:
        Dict containing job ID, formatted prompt, and status
    """
    try:
        # Parse the event
        if 'body' in event:
            # If coming from API Gateway
            body = json.loads(event['body'])
            job_id = body.get('job_id')
            client_data = body.get('client_data')
        else:
            # If coming from direct Lambda invocation
            job_id = event.get('job_id')
            client_data = event.get('client_data')
        
        logger.info(f"Formatting prompt for job: {job_id}")
        
        if not job_id or not client_data:
            logger.error("Missing required parameters: job_id or client_data")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Update job status
        utils.update_job_status(job_id, utils.JobStatus.FORMATTING_PROMPT)
        
        # Get the standard prompt template
        prompt = get_standard_prompt()
        
        # Store the standard prompt and client data (separately) in S3
        prompt_key = f"jobs/{job_id}/prompt.txt"
        client_data_key = f"jobs/{job_id}/client_data.json"
        
        utils.write_to_s3(utils.OUTPUT_BUCKET, prompt_key, prompt, 'text/plain')
        utils.write_to_s3(utils.OUTPUT_BUCKET, client_data_key, json.dumps(client_data), 'application/json')
        
        logger.info(f"Prompt template and client data stored for job: {job_id}")
        
        # Prepare result for next step
        result = {
            'job_id': job_id,
            'prompt': prompt,
            'prompt_key': prompt_key,
            'client_data': client_data,
            'client_data_key': client_data_key,
            'status': utils.JobStatus.CALLING_AI
        }
        
        # Update job status to indicate we're moving to call AI
        utils.update_job_status(job_id, utils.JobStatus.CALLING_AI)
        
        logger.info(f"Job {job_id} proceeding to call_gemini")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error in format_prompt: {str(e)}", exc_info=True)
        
        # Update job status to failed if we have a job ID
        if 'job_id' in locals() and job_id:
            utils.update_job_status(job_id, utils.JobStatus.FAILED, str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 