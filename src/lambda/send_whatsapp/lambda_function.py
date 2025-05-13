import json
import os
import sys
import logging
import boto3
import requests
from botocore.exceptions import ClientError

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_manager = boto3.client('secretsmanager')
s3 = boto3.client('s3')

# Constants
WHATSAPP_API_SECRET_NAME = os.environ.get('WHATSAPP_API_SECRET_NAME', 'HRIM/WhatsApp/ApiKey')
WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v18.0/FROM_PHONE_ID/messages')

def lambda_handler(event, context):
    """
    Lambda function to send the generated PDF to the client via WhatsApp.
    
    Args:
        event (dict): Input event containing job_id, output_s3_bucket, output_s3_key, presigned_url
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Status of WhatsApp sending and job ID
    """
    logger.info(f"Received event for sending WhatsApp message")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        output_s3_bucket = event.get('output_s3_bucket')
        output_s3_key = event.get('output_s3_key')
        presigned_url = event.get('presigned_url')
        
        if not all([job_id, output_s3_bucket, output_s3_key]):
            error_message = "Missing required parameters in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Update job status
        utils.update_job_status(job_id, 'SENDING_WHATSAPP')
        
        # Get job details for client info
        job = utils.get_job(job_id)
        client_whatsapp = job.get('client_whatsapp')
        client_name = job.get('client_name', 'Valued Client')
        
        if not client_whatsapp or client_whatsapp == 'pending_extraction' or client_whatsapp == 'missing':
            error_message = "Client WhatsApp number is missing or invalid"
            logger.error(error_message)
            utils.update_job_status(job_id, 'WHATSAPP_FAILED', {'error_details': error_message})
            return {
                'statusCode': 400,
                'error': error_message,
                'job_id': job_id
            }
        
        # Get WhatsApp API key from Secrets Manager
        whatsapp_api_details = get_whatsapp_api_details()
        if not whatsapp_api_details:
            error_message = "Failed to retrieve WhatsApp API details"
            utils.handle_error(job_id, error_message)
            return {
                'statusCode': 500,
                'error': error_message,
                'job_id': job_id
            }
        
        # We need to have a publicly accessible URL for the PDF for WhatsApp Business API
        # If presigned_url is not available, try to generate one
        if not presigned_url:
            try:
                presigned_url = s3.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': output_s3_bucket,
                        'Key': output_s3_key
                    },
                    ExpiresIn=86400  # 24 hours
                )
                logger.info(f"Generated presigned URL for WhatsApp")
            except ClientError as e:
                logger.warning(f"Could not generate presigned URL: {str(e)}")
                presigned_url = None
        
        # Send message via WhatsApp Business API
        try:
            # Prepare message
            filename = output_s3_key.split('/')[-1]
            
            # Example of sending a template message with a document link using the WhatsApp Business API
            # Note: The exact payload structure might vary depending on the WhatsApp provider
            api_url = whatsapp_api_details.get('api_url', WHATSAPP_API_URL)
            access_token = whatsapp_api_details.get('access_token')
            
            if presigned_url:
                # Send message with document link
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": client_whatsapp,
                    "type": "template",
                    "template": {
                        "name": "wellness_plan_ready",
                        "language": {
                            "code": "en"
                        },
                        "components": [
                            {
                                "type": "header",
                                "parameters": [
                                    {
                                        "type": "document",
                                        "document": {
                                            "link": presigned_url,
                                            "filename": filename
                                        }
                                    }
                                ]
                            },
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text",
                                        "text": client_name
                                    }
                                ]
                            }
                        ]
                    }
                }
            else:
                # Send text-only message if document can't be sent
                payload = {
                    "messaging_product": "whatsapp",
                    "to": client_whatsapp,
                    "type": "text",
                    "text": {
                        "body": f"Hello {client_name}, your personalized wellness plan is ready! Please check your email for the document."
                    }
                }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.post(api_url, json=payload, headers=headers)
            
            if response.status_code in (200, 201):
                logger.info(f"Successfully sent WhatsApp message to {client_whatsapp}")
                whatsapp_status = "SUCCESS"
                whatsapp_message_id = response.json().get('messages', [{}])[0].get('id', 'Unknown')
            else:
                error_message = f"Error sending WhatsApp message: {response.text}"
                logger.error(error_message)
                whatsapp_status = "FAILED"
                whatsapp_message_id = None
            
        except Exception as e:
            error_message = f"Error sending WhatsApp message: {str(e)}"
            logger.error(error_message)
            whatsapp_status = "FAILED"
            whatsapp_message_id = None
        
        # Update job with WhatsApp status
        additional_data = {
            'whatsapp_status': whatsapp_status,
            'whatsapp_message_id': whatsapp_message_id
        }
        utils.update_job_status(job_id, 'WHATSAPP_SENT', additional_data)
        
        # Return the WhatsApp status and job ID
        return {
            'job_id': job_id,
            'whatsapp_status': whatsapp_status,
            'whatsapp_message_id': whatsapp_message_id
        }
    
    except Exception as e:
        error_message = f"Error in send_whatsapp: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def get_whatsapp_api_details():
    """
    Get WhatsApp API details from AWS Secrets Manager.
    
    Returns:
        dict: WhatsApp API details (api_url, access_token, etc.)
    """
    try:
        response = secrets_manager.get_secret_value(
            SecretId=WHATSAPP_API_SECRET_NAME
        )
        secret = json.loads(response['SecretString'])
        
        # Expected structure: {"api_url": "URL", "access_token": "TOKEN"}
        return secret
    except ClientError as e:
        logger.error(f"Error retrieving WhatsApp API details: {str(e)}")
        return None 