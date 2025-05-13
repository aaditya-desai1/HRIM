"""
Upload PDF lambda function.

This function handles the final storage of the PDF in the designated S3 location
and prepares for the email delivery step.
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

# Initialize S3 client
s3_client = boto3.client('s3')

def generate_s3_presigned_url(bucket: str, key: str, expiration: int = 604800) -> str:
    """
    Generate a presigned URL for an S3 object.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiration: URL expiration time in seconds (default 7 days)
        
    Returns:
        Presigned URL string
    """
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
        return response
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict containing job_id, pdf_key, and client_data
        context: Lambda context
        
    Returns:
        Dict containing job ID, PDF URL, and status
    """
    try:
        # Parse the event
        if 'body' in event:
            # If coming from API Gateway
            body = json.loads(event['body'])
            job_id = body.get('job_id')
            pdf_key = body.get('pdf_key')
            pdf_filename = body.get('pdf_filename')
            client_data = body.get('client_data')
        else:
            # If coming from direct Lambda invocation
            job_id = event.get('job_id')
            pdf_key = event.get('pdf_key')
            pdf_filename = event.get('pdf_filename')
            client_data = event.get('client_data')
        
        logger.info(f"Processing PDF upload for job: {job_id}")
        
        if not job_id or not pdf_key or not client_data:
            logger.error("Missing required parameters: job_id, pdf_key, or client_data")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Update job status
        utils.update_job_status(job_id, utils.JobStatus.UPLOADING_PDF)
        
        # Generate a presigned URL for the PDF
        pdf_url = generate_s3_presigned_url(utils.OUTPUT_BUCKET, pdf_key)
        
        # Add PDF URL to job record
        job_table = boto3.resource('dynamodb').Table(utils.JOB_TABLE_NAME)
        job_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET pdf_key = :pdf_key, pdf_url = :pdf_url",
            ExpressionAttributeValues={
                ':pdf_key': pdf_key,
                ':pdf_url': pdf_url
            }
        )
        
        logger.info(f"PDF URL generated and stored for job: {job_id}")
        
        # Prepare result for next step
        result = {
            'job_id': job_id,
            'pdf_key': pdf_key,
            'pdf_filename': pdf_filename,
            'pdf_url': pdf_url,
            'client_data': client_data,
            'status': utils.JobStatus.SENDING_EMAIL
        }
        
        # Update job status to indicate we're moving to send email
        utils.update_job_status(job_id, utils.JobStatus.SENDING_EMAIL)
        
        logger.info(f"Job {job_id} proceeding to send_email")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error in upload_pdf: {str(e)}", exc_info=True)
        
        # Update job status to failed if we have a job ID
        if 'job_id' in locals() and job_id:
            error_message = f"PDF upload error: {str(e)}"
            utils.update_job_status(job_id, utils.JobStatus.FAILED, error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 