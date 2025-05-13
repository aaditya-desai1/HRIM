import json
import uuid
import os
import sys
import logging
import boto3
from datetime import datetime
import urllib.parse

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
step_functions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')

# Environment variables
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME', 'WellnessPlanJobs')

def lambda_handler(event, context):
    """
    Lambda function to process S3 events and initiate the wellness plan generation workflow.
    
    Args:
        event (dict): Event data from S3
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Response with job ID and status
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract S3 bucket and key from the event
        for record in event.get('Records', []):
            if record.get('eventSource') == 'aws:s3' and record.get('eventName').startswith('ObjectCreated:'):
                s3_event = record.get('s3', {})
                bucket_name = s3_event.get('bucket', {}).get('name')
                object_key = urllib.parse.unquote_plus(s3_event.get('object', {}).get('key'))
                
                # Generate a unique job ID
                job_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                
                # Create an entry in the jobs table
                jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
                jobs_table.put_item(
                    Item={
                        'job_id': job_id,
                        'input_s3_bucket': bucket_name,
                        'input_s3_key': object_key,
                        'status': 'PENDING',
                        'start_time': timestamp,
                        'client_email': 'pending_extraction',
                        'client_whatsapp': 'pending_extraction',
                        'client_name': 'pending_extraction'
                    }
                )
                
                logger.info(f"Created job record with ID: {job_id}")
                
                # Start Step Functions execution
                if STATE_MACHINE_ARN:
                    response = step_functions.start_execution(
                        stateMachineArn=STATE_MACHINE_ARN,
                        name=f"WellnessPlan-{job_id}",
                        input=json.dumps({
                            'job_id': job_id,
                            'input_s3_bucket': bucket_name,
                            'input_s3_key': object_key,
                            'timestamp': timestamp
                        })
                    )
                    
                    logger.info(f"Started Step Functions execution: {response['executionArn']}")
                    
                    # Update job with execution ARN
                    jobs_table.update_item(
                        Key={'job_id': job_id},
                        UpdateExpression="SET execution_arn = :arn",
                        ExpressionAttributeValues={':arn': response['executionArn']}
                    )
                    
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Processing initiated successfully',
                            'job_id': job_id,
                            'execution_arn': response['executionArn']
                        })
                    }
                else:
                    error_message = "STATE_MACHINE_ARN environment variable not configured"
                    logger.error(error_message)
                    utils.handle_error(job_id, error_message)
                    return {
                        'statusCode': 500,
                        'body': json.dumps({
                            'error': error_message
                        })
                    }
    
    except Exception as e:
        logger.error(f"Error processing trigger: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Failed to process trigger: {str(e)}"
            })
        }
    
    return {
        'statusCode': 400,
        'body': json.dumps({
            'error': 'No valid S3 event found in the event payload'
        })
    } 