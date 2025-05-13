import json
import os
import sys
import logging
import boto3
from datetime import datetime

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Constants
JOBS_TABLE_NAME = os.environ.get('JOBS_TABLE_NAME', 'WellnessPlanJobs')
NOTIFICATION_TOPIC_ARN = os.environ.get('NOTIFICATION_TOPIC_ARN')

def lambda_handler(event, context):
    """
    Lambda function to complete the wellness plan generation job.
    
    Args:
        event (dict): Input event containing job_id, email_status, whatsapp_status
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Final job status
    """
    logger.info(f"Received event for job completion")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        email_status = event.get('email_status')
        whatsapp_status = event.get('whatsapp_status')
        
        if not job_id:
            error_message = "Missing job_id in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Get job details
        job = utils.get_job(job_id)
        
        # Determine final status based on email and WhatsApp delivery
        if email_status == "SUCCESS" and whatsapp_status == "SUCCESS":
            final_status = "COMPLETED"
            error_details = None
        elif email_status == "SUCCESS" or whatsapp_status == "SUCCESS":
            final_status = "COMPLETED_WITH_WARNINGS"
            error_details = "One of the delivery channels failed"
        else:
            final_status = "COMPLETED_WITH_ERRORS"
            error_details = "Both delivery channels failed"
        
        # Calculate processing time
        start_time = job.get('start_time')
        completion_time = datetime.utcnow().isoformat()
        
        # Convert string timestamps to datetime objects for calculation
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                completion_dt = datetime.fromisoformat(completion_time)
                
                # Calculate processing time in seconds
                processing_time_seconds = (completion_dt - start_dt).total_seconds()
                processing_time_minutes = processing_time_seconds / 60
                
                # Check if we met the 2-hour SLA
                sla_met = processing_time_minutes <= 120  # 2 hours = 120 minutes
            except Exception as e:
                logger.warning(f"Error calculating processing time: {str(e)}")
                processing_time_seconds = None
                processing_time_minutes = None
                sla_met = None
        else:
            processing_time_seconds = None
            processing_time_minutes = None
            sla_met = None
        
        # Update job with final status
        additional_data = {
            'completion_time': completion_time,
            'processing_time_seconds': processing_time_seconds,
            'processing_time_minutes': processing_time_minutes,
            'sla_met': sla_met
        }
        
        if error_details:
            additional_data['error_details'] = error_details
        
        utils.update_job_status(job_id, final_status, additional_data)
        
        # Log completion
        logger.info(f"Job {job_id} completed with status {final_status}")
        logger.info(f"Processing time: {processing_time_minutes} minutes (SLA met: {sla_met})")
        
        # Send notification if topic ARN is configured
        if NOTIFICATION_TOPIC_ARN:
            send_completion_notification(job_id, final_status, job, processing_time_minutes, sla_met)
        
        # Return the final status
        return {
            'job_id': job_id,
            'final_status': final_status,
            'processing_time_minutes': processing_time_minutes,
            'sla_met': sla_met
        }
    
    except Exception as e:
        error_message = f"Error in complete_job: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def send_completion_notification(job_id, status, job, processing_time, sla_met):
    """
    Send a completion notification via SNS.
    
    Args:
        job_id (str): Job ID
        status (str): Final job status
        job (dict): Job details
        processing_time (float): Processing time in minutes
        sla_met (bool): Whether the SLA was met
    """
    try:
        client_name = job.get('client_name', 'Unknown Client')
        client_email = job.get('client_email', 'Unknown Email')
        
        subject = f"Wellness Plan Job {job_id} Completed: {status}"
        
        message = {
            'job_id': job_id,
            'status': status,
            'client_name': client_name,
            'client_email': client_email,
            'processing_time_minutes': processing_time,
            'sla_met': sla_met,
            'completion_time': datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn=NOTIFICATION_TOPIC_ARN,
            Subject=subject,
            Message=json.dumps(message)
        )
        
        logger.info(f"Sent completion notification for job {job_id}")
    except Exception as e:
        logger.error(f"Error sending completion notification: {str(e)}")
        # Non-critical error, don't raise exception 