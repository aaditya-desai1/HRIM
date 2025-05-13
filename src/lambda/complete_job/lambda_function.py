"""
Complete job lambda function.

This function marks the job as complete and performs any final cleanup or notification tasks.
"""

import json
import os
import logging
import sys
import boto3
from datetime import datetime

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def update_job_status(job_id, status, error_message=None):
    """
    Update job status in DynamoDB.
    
    Args:
        job_id: The job ID
        status: New status to set
        error_message: Optional error message
    """
    try:
        # Get DynamoDB table
        job_table = boto3.resource('dynamodb').Table(utils.JOB_TABLE_NAME)
        
        # Prepare update expression and values
        update_expression = "SET #job_status = :status, updated_at = :updated_at"
        expression_values = {
            ':status': status,
            ':updated_at': datetime.now().isoformat()
        }
        
        # Expression attribute names to handle reserved keywords
        expression_names = {
            '#job_status': 'status'
        }
        
        # Add error message if provided
        if error_message:
            update_expression += ", error_message = :error_message"
            expression_values[':error_message'] = error_message
        
        # Add completion timestamp if status is COMPLETED
        if status == "COMPLETED":
            update_expression += ", completed_at = :completed_at, completed = :completed"
            expression_values[':completed_at'] = datetime.now().isoformat()
            expression_values[':completed'] = True
        
        # Update item in DynamoDB
        job_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        
        logger.info(f"Updated job {job_id} status to {status}")
    
    except Exception as e:
        logger.error(f"Failed to update job status: {str(e)}")
        raise

def extract_job_id(event):
    """
    Extract job_id from the event, handling different input formats.
    
    Args:
        event: The Lambda event object
        
    Returns:
        The job_id if found, None otherwise
    """
    logger.info(f"Extracting job_id from event: {json.dumps(event)}")
    
    # Check if this is a Step Functions state machine input
    if isinstance(event, dict) and 'body' in event:
        # This could be from API Gateway or a previous Step Function state
        try:
            # If body is a string (from API Gateway), parse it
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                # If body is already a dict (from Step Function), use it directly
                body = event['body']
                
            return body.get('job_id')
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing event body: {str(e)}")
            # Try direct access as fallback
            pass
    
    # Direct event access (direct Lambda invocation)
    return event.get('job_id')

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: Dict containing job_id
        context: Lambda context
        
    Returns:
        Response with status
    """
    try:
        logger.info(f"Received complete job event: {json.dumps(event)}")
        
        # Extract job ID from event using helper function
        job_id = extract_job_id(event)
        
        if not job_id:
            raise ValueError("Missing required parameter: job_id")
        
        # Update job status in DynamoDB
        update_job_status(job_id, "COMPLETED")
        
        logger.info(f"Job {job_id} completed successfully")
        
        # No delay for immediate completion
        # NOTE: Removed any waiting or delay here to ensure instant processing
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'job_id': job_id,
                'status': 'COMPLETED',
                'message': 'Job completed successfully with immediate notification.'
            })
        }
    
    except Exception as e:
        logger.error(f"Error completing job: {str(e)}", exc_info=True)
        
        # Try to update job status to ERROR if we have a job_id
        job_id = None
        try:
            job_id = extract_job_id(event)
            if job_id:
                update_job_status(job_id, "ERROR", str(e))
        except Exception as update_error:
            logger.error(f"Failed to update job status: {str(update_error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to complete job',
                'details': str(e)
            })
        } 