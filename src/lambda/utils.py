import boto3
import json
import os
import logging
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sns = boto3.client('sns')
ses = boto3.client('ses')

# Constants
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME', 'WellnessPlanJobs')
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'wellness-data-input')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'wellness-plan-output')

# DynamoDB functions
def get_jobs_table():
    """Return the DynamoDB jobs table resource."""
    return dynamodb.Table(JOBS_TABLE_NAME)

def update_job_status(job_id, status, additional_data=None):
    """
    Update the status of a job in DynamoDB.
    
    Args:
        job_id (str): The unique job identifier
        status (str): The new status
        additional_data (dict, optional): Additional data to update
    
    Returns:
        dict: The response from DynamoDB
    """
    table = get_jobs_table()
    update_expression = "SET #status = :status"
    expression_attribute_names = {'#status': 'status'}
    expression_attribute_values = {':status': status}
    
    if additional_data:
        for key, value in additional_data.items():
            update_expression += f", #{key} = :{key}"
            expression_attribute_names[f'#{key}'] = key
            expression_attribute_values[f':{key}'] = value
    
    try:
        response = table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )
        logger.info(f"Updated job {job_id} status to {status}")
        return response
    except ClientError as e:
        logger.error(f"Error updating job status: {e}")
        raise

def get_job(job_id):
    """
    Get job details from DynamoDB.
    
    Args:
        job_id (str): The unique job identifier
    
    Returns:
        dict: The job details
    """
    table = get_jobs_table()
    try:
        response = table.get_item(Key={'job_id': job_id})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error getting job details: {e}")
        raise

# S3 functions
def read_from_s3(bucket, key):
    """
    Read and parse JSON data from S3.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
    
    Returns:
        dict: Parsed JSON data
    """
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except ClientError as e:
        logger.error(f"Error reading from S3: {e}")
        raise
    except json.JSONDecodeError:
        logger.error("Error parsing JSON from S3")
        raise

def write_to_s3(bucket, key, data, content_type='application/pdf'):
    """
    Write data to S3.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        data (bytes): Data to write
        content_type (str): Content type of the data
    
    Returns:
        dict: S3 put_object response
    """
    try:
        response = s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        logger.info(f"Successfully wrote to S3: {bucket}/{key}")
        return response
    except ClientError as e:
        logger.error(f"Error writing to S3: {e}")
        raise

# Error handling
def handle_error(job_id, error_message, error_details=None):
    """
    Handle error by updating job status and logging.
    
    Args:
        job_id (str): The unique job identifier
        error_message (str): Error message
        error_details (dict, optional): Additional error details
    """
    logger.error(f"Error processing job {job_id}: {error_message}")
    if error_details:
        logger.error(f"Error details: {json.dumps(error_details)}")
    
    additional_data = {
        'error_details': error_message
    }
    
    try:
        update_job_status(job_id, 'FAILED', additional_data)
    except Exception as e:
        logger.error(f"Failed to update job status to FAILED: {e}") 