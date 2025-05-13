import json
import os
import sys
import logging
import boto3
import base64
from botocore.exceptions import ClientError

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses = boto3.client('ses')
s3 = boto3.client('s3')

# Constants
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@example.com')
EMAIL_SUBJECT = os.environ.get('EMAIL_SUBJECT', 'Your Personalized Wellness Plan')
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'

def lambda_handler(event, context):
    """
    Lambda function to send the generated PDF to the client via email.
    
    Args:
        event (dict): Input event containing job_id, output_s3_bucket, output_s3_key
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Status of email sending and job ID
    """
    logger.info(f"Received event for sending email")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        output_s3_bucket = event.get('output_s3_bucket')
        output_s3_key = event.get('output_s3_key')
        presigned_url = event.get('presigned_url')
        
        # For testing - if specifically passing an email address in the event
        test_recipient = event.get('test_recipient')
        
        if not all([job_id, output_s3_bucket, output_s3_key]):
            error_message = "Missing required parameters in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Update job status
        utils.update_job_status(job_id, 'SENDING_EMAIL')
        
        # Get job details for client info
        job = utils.get_job(job_id)
        client_email = test_recipient or job.get('client_email')
        client_name = job.get('client_name', 'Valued Client')
        
        if not client_email or client_email == 'pending_extraction' or client_email == 'missing@example.com':
            error_message = "Client email address is missing or invalid"
            logger.error(error_message)
            utils.update_job_status(job_id, 'EMAIL_FAILED', {'error_details': error_message})
            return {
                'statusCode': 400,
                'error': error_message,
                'job_id': job_id
            }
        
        # Fetch PDF from S3
        try:
            logger.info(f"Fetching PDF from S3: {output_s3_bucket}/{output_s3_key}")
            response = s3.get_object(Bucket=output_s3_bucket, Key=output_s3_key)
            pdf_data = response['Body'].read()
        except ClientError as e:
            error_message = f"Error fetching PDF from S3: {str(e)}"
            utils.handle_error(job_id, error_message)
            return {
                'statusCode': 500,
                'error': error_message,
                'job_id': job_id
            }
        
        # Send email with PDF attachment using SES
        try:
            # Prepare email
            filename = output_s3_key.split('/')[-1]
            
            email_body_text = f"""
Hello {client_name},

Your personalized wellness plan is attached to this email. This plan has been specifically created for you based on the information you provided.

The plan includes:
- 4-Week Meal Plan
- Weekly Daily Routine Chart
- Weekly Grocery Lists
- DOs & DON'Ts
- Stress & Balance Tips
- Summary & Follow-up Recommendations

If you have any questions about your plan, please reply to this email.

Thank you for choosing our wellness planning service!
            """
            
            email_body_html = f"""
<html>
<head></head>
<body>
    <p>Hello {client_name},</p>
    
    <p>Your personalized wellness plan is attached to this email. This plan has been specifically created for you based on the information you provided.</p>
    
    <p>The plan includes:</p>
    <ul>
        <li>4-Week Meal Plan</li>
        <li>Weekly Daily Routine Chart</li>
        <li>Weekly Grocery Lists</li>
        <li>DOs &amp; DON'Ts</li>
        <li>Stress &amp; Balance Tips</li>
        <li>Summary &amp; Follow-up Recommendations</li>
    </ul>
    
    <p>If you have any questions about your plan, please reply to this email.</p>
    
    <p>Thank you for choosing our wellness planning service!</p>
</body>
</html>
            """
            
            # If in debug mode, log additional information
            if DEBUG_MODE:
                logger.info(f"Sending email from: {SENDER_EMAIL}")
                logger.info(f"Sending email to: {client_email}")
                logger.info(f"Email subject: {EMAIL_SUBJECT}")
                logger.info(f"PDF attachment size: {len(pdf_data)} bytes")
                
                # Check SES sending limits
                try:
                    quota = ses.get_send_quota()
                    logger.info(f"SES quota - Max24HourSend: {quota['Max24HourSend']}, SentLast24Hours: {quota['SentLast24Hours']}")
                except Exception as quota_error:
                    logger.warning(f"Could not retrieve SES quota: {str(quota_error)}")
            
            # Create raw email message (with attachment)
            response = ses.send_raw_email(
                Source=SENDER_EMAIL,
                Destinations=[client_email],
                RawMessage={
                    'Data': create_raw_email_with_attachment(
                        sender=SENDER_EMAIL,
                        recipients=[client_email],
                        subject=EMAIL_SUBJECT,
                        text_body=email_body_text,
                        html_body=email_body_html,
                        attachment=pdf_data,
                        filename=filename
                    )
                }
            )
            
            logger.info(f"Successfully sent email to {client_email}")
            email_status = "SUCCESS"
            email_message_id = response.get('MessageId', 'Unknown')
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Provide more detailed error messages for common SES issues
            if error_code == 'MessageRejected':
                error_message = f"Email rejected: {error_message}. Check if your sending address is verified in SES."
            elif error_code == 'MailFromDomainNotVerified':
                error_message = f"Domain not verified: {error_message}. Verify your domain in SES."
            elif error_code == 'EmailAddressNotVerified':
                error_message = f"Email address not verified: {error_message}. Verify your email in SES."
            elif error_code == 'Throttling':
                error_message = f"SES throttling: {error_message}. Check your sending limits."
            else:
                error_message = f"Error sending email ({error_code}): {error_message}"
                
            logger.error(error_message)
            email_status = "FAILED"
            email_message_id = None
        
        # Update job with email status
        additional_data = {
            'email_status': email_status,
            'email_message_id': email_message_id
        }
        utils.update_job_status(job_id, 'EMAIL_SENT', additional_data)
        
        # Return the email status and job ID
        return {
            'job_id': job_id,
            'email_status': email_status,
            'email_message_id': email_message_id
        }
    
    except Exception as e:
        error_message = f"Error in send_email: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def create_raw_email_with_attachment(sender, recipients, subject, text_body, html_body, attachment, filename):
    """
    Create a raw email message with attachment.
    
    Args:
        sender (str): Sender email address
        recipients (list): List of recipient email addresses
        subject (str): Email subject
        text_body (str): Plain text email body
        html_body (str): HTML email body
        attachment (bytes): Attachment data
        filename (str): Attachment filename
        
    Returns:
        bytes: Raw email message
    """
    import email.utils
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg['Date'] = email.utils.formatdate()
    
    # Create alternative part (text/html)
    alt = MIMEMultipart('alternative')
    
    # Attach text body
    textpart = MIMEText(text_body.encode('utf-8'), 'plain', 'utf-8')
    alt.attach(textpart)
    
    # Attach HTML body
    htmlpart = MIMEText(html_body.encode('utf-8'), 'html', 'utf-8')
    alt.attach(htmlpart)
    
    # Attach the multipart/alternative child container to the multipart/mixed parent container
    msg.attach(alt)
    
    # Add attachment
    att = MIMEApplication(attachment)
    att.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(att)
    
    return msg.as_string().encode('utf-8') 