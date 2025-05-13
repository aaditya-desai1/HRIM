import json
import os
import sys
import logging
import boto3
from botocore.exceptions import ClientError

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Constants
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME', 'WellnessPlanJobs')

def lambda_handler(event, context):
    """
    Lambda function to fetch client data from S3 and extract key information.
    
    Args:
        event (dict): Input event containing job_id, input_s3_bucket, and input_s3_key
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Extracted client data and job ID
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        input_s3_bucket = event.get('input_s3_bucket')
        input_s3_key = event.get('input_s3_key')
        
        if not all([job_id, input_s3_bucket, input_s3_key]):
            error_message = "Missing required parameters in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Update job status
        utils.update_job_status(job_id, 'FETCHING_DATA')
        
        # Fetch data from S3
        logger.info(f"Fetching data from s3://{input_s3_bucket}/{input_s3_key}")
        try:
            client_data = utils.read_from_s3(input_s3_bucket, input_s3_key)
        except Exception as e:
            error_message = f"Failed to read data from S3: {str(e)}"
            utils.handle_error(job_id, error_message)
            return {
                'statusCode': 500,
                'error': error_message
            }
        
        # Extract key client information for job tracking and messaging
        client_email = clean_email(client_data.get("Email", ""))
        client_whatsapp = clean_phone(client_data.get("WhatsApp Contact Number", ""))
        client_name = client_data.get("Full Name", "Client")
        
        # Update job with contact info
        additional_data = {
            'client_email': client_email,
            'client_whatsapp': client_whatsapp,
            'client_name': client_name
        }
        utils.update_job_status(job_id, 'DATA_FETCHED', additional_data)
        
        logger.info(f"Successfully fetched and parsed data for job {job_id}")
        
        # Return the client data and job ID for the next step
        return {
            'job_id': job_id,
            'client_data': client_data,
            'client_email': client_email,
            'client_whatsapp': client_whatsapp,
            'client_name': client_name
        }
    
    except Exception as e:
        error_message = f"Error in fetch_data: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def clean_email(email):
    """
    Clean email address by removing 'mailto:' prefix if present.
    
    Args:
        email (str): Raw email string
        
    Returns:
        str: Cleaned email address
    """
    if not email:
        return "missing@example.com"
    
    # Remove mailto: prefix if present
    return email.replace("mailto:", "").strip()

def clean_phone(phone):
    """
    Clean phone number by removing formatting characters.
    
    Args:
        phone (str): Raw phone number string
        
    Returns:
        str: Cleaned phone number
    """
    if not phone:
        return "missing"
    
    # Remove common formatting characters
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Ensure it starts with a plus sign for international format
    if cleaned and not cleaned.startswith('+'):
        if cleaned.startswith('00'):
            cleaned = '+' + cleaned[2:]
        else:
            # Default to India country code if no country code is provided
            cleaned = '+91' + cleaned
            
    return cleaned 