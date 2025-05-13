"""
Fetch data lambda function.

This function retrieves client data from S3 based on the key provided in the event.
It then passes the data to the next step in the workflow.
"""

import json
import os
import logging
import sys

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict containing job_id and client_data_key
        context: Lambda context
        
    Returns:
        Dict containing job ID, client data, and status
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract job ID and S3 key from the event
        job_id = event.get('job_id')
        client_data_key = event.get('client_data_key')
        
        if not job_id or not client_data_key:
            logger.error("Missing required parameters: job_id or client_data_key")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Update job status to indicate we're fetching data
        utils.update_job_status(job_id, utils.JobStatus.FETCHING_DATA)
        
        logger.info(f"Fetching client data from S3: {client_data_key}")
        
        # Read client data from S3
        client_data = utils.read_s3_json(utils.INPUT_BUCKET, client_data_key)
        
        logger.info(f"Successfully fetched client data for job {job_id}")
        
        # Validate required fields in client data
        required_fields = [
            'Full Name', 
            'Email', 
            'Height', 
            'Weight', 
            'Wellness Goals'
        ]
        
        missing_fields = [field for field in required_fields if field not in client_data]
        if missing_fields:
            error_msg = f"Missing required fields in client data: {', '.join(missing_fields)}"
            logger.error(error_msg)
            utils.update_job_status(job_id, utils.JobStatus.FAILED, error_msg)
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_msg})
            }
        
        # Store the client data in S3 as part of the job artifacts
        client_data_json = json.dumps(client_data)
        client_data_artifact_key = f"jobs/{job_id}/client_data.json"
        utils.write_to_s3(utils.OUTPUT_BUCKET, client_data_artifact_key, client_data_json)
        
        # Prepare the result to pass to the next step
        result = {
            'job_id': job_id,
            'client_data': client_data,
            'client_data_key': client_data_key,
            'client_data_artifact_key': client_data_artifact_key,
            'status': utils.JobStatus.FORMATTING_PROMPT
        }
        
        # Update job status to indicate we're moving to format prompt
        utils.update_job_status(job_id, utils.JobStatus.FORMATTING_PROMPT)
        
        logger.info(f"Job {job_id} proceeding to format_prompt")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error in fetch_data: {str(e)}", exc_info=True)
        
        # Update job status to failed if we have a job ID
        if 'job_id' in locals() and job_id:
            utils.update_job_status(job_id, utils.JobStatus.FAILED, str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 