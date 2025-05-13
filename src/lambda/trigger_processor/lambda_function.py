"""
Trigger processor lambda function.

This function is triggered by S3 event when a new client data file is uploaded.
It extracts the S3 key from the event and initiates a new wellness plan generation job.
"""

import json
import os
import logging
import sys
import urllib.parse
import boto3

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get Step Functions ARN from environment variables
STEP_FUNCTION_ARN = os.environ.get('STEP_FUNCTION_ARN')

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict (containing S3 event details)
        context: Lambda context
        
    Returns:
        Dict containing job ID and status
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract bucket name and file key from the S3 event
        jobs = []
        
        for record in event.get('Records', []):
            if record.get('eventSource') != 'aws:s3':
                continue
                
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing new file: s3://{bucket}/{key}")
            
            # Only process files in the 'incoming/' directory
            if not key.startswith('incoming/'):
                logger.info(f"Skipping file outside of incoming directory: {key}")
                continue
                
            # Generate a new job ID
            job_id = utils.generate_job_id()
            
            # Create a job record in DynamoDB
            job_record = utils.create_job_record(job_id, key)
            
            # Add job to the list
            jobs.append({
                'job_id': job_id,
                'client_data_key': key,
                'status': utils.JobStatus.CREATED
            })
            
            # Start the Step Functions workflow if ARN is available
            if STEP_FUNCTION_ARN:
                try:
                    # Initialize the Step Functions client
                    sfn_client = boto3.client('stepfunctions')
                    
                    # Prepare the input for the Step Functions workflow
                    workflow_input = {
                        'job_id': job_id,
                        'client_data_key': key
                    }
                    
                    # Start the workflow execution
                    sfn_response = sfn_client.start_execution(
                        stateMachineArn=STEP_FUNCTION_ARN,
                        name=f"job-{job_id}",
                        input=json.dumps(workflow_input)
                    )
                    
                    logger.info(f"Started Step Functions workflow: {sfn_response['executionArn']}")
                    
                    # Update job record with execution ARN
                    utils.update_job_record(job_id, {
                        'execution_arn': sfn_response['executionArn'],
                        'status': utils.JobStatus.FETCHING_DATA
                    })
                except Exception as e:
                    logger.error(f"Error starting Step Functions workflow: {str(e)}", exc_info=True)
            else:
                logger.warning("STEP_FUNCTION_ARN not configured. Skipping workflow start.")
                
        # Return the list of created jobs
        result = {
            'jobs': jobs
        }
        
        logger.info(f"Created {len(jobs)} jobs")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    
    except Exception as e:
        logger.error(f"Error in trigger_processor: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 