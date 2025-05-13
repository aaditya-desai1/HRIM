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

# Constants
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'wellness-plan-output')

def lambda_handler(event, context):
    """
    Lambda function to upload the generated PDF to S3.
    
    Args:
        event (dict): Input event containing job_id and pdf_data
        context (LambdaContext): Lambda context
        
    Returns:
        dict: S3 location of uploaded PDF and job ID
    """
    logger.info(f"Received event for PDF upload to S3")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        pdf_data = event.get('pdf_data')
        
        if not all([job_id, pdf_data]):
            error_message = "Missing required parameters in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Update job status
        utils.update_job_status(job_id, 'UPLOADING_PDF')
        
        # Get job details for client info
        job = utils.get_job(job_id)
        client_name = job.get('client_name', 'client')
        
        # Sanitize client name for S3 key
        sanitized_name = sanitize_filename(client_name)
        
        # Create S3 key for the PDF
        s3_key = f"plans/{job_id}/{sanitized_name}_wellness_plan.pdf"
        
        # Convert the PDF data from Base64 encoding back to binary
        binary_pdf_data = pdf_data.encode('latin1')
        
        # Upload PDF to S3
        try:
            s3_response = s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=s3_key,
                Body=binary_pdf_data,
                ContentType='application/pdf'
            )
            logger.info(f"Successfully uploaded PDF to S3: {OUTPUT_BUCKET}/{s3_key}")
        except ClientError as e:
            error_message = f"Error uploading PDF to S3: {str(e)}"
            utils.handle_error(job_id, error_message)
            return {
                'statusCode': 500,
                'error': error_message
            }
        
        # Create presigned URL for the PDF (30 min expiration)
        try:
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': OUTPUT_BUCKET,
                    'Key': s3_key
                },
                ExpiresIn=1800  # 30 minutes
            )
            logger.info(f"Created presigned URL for PDF")
        except ClientError as e:
            logger.warning(f"Could not generate presigned URL: {str(e)}")
            presigned_url = None
        
        # Update job with S3 location
        additional_data = {
            'output_s3_bucket': OUTPUT_BUCKET,
            'output_s3_key': s3_key,
            'presigned_url': presigned_url
        }
        utils.update_job_status(job_id, 'PDF_UPLOADED', additional_data)
        
        # Return the S3 location and job ID for the next step
        return {
            'job_id': job_id,
            'output_s3_bucket': OUTPUT_BUCKET,
            'output_s3_key': s3_key,
            'presigned_url': presigned_url
        }
    
    except Exception as e:
        error_message = f"Error in upload_pdf: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def sanitize_filename(filename):
    """
    Sanitize filename for use in S3 keys.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Replace spaces with underscores and remove special characters
    sanitized = ''.join(c if c.isalnum() or c in ['_', '-', '.'] else '_' for c in filename.replace(' ', '_'))
    return sanitized