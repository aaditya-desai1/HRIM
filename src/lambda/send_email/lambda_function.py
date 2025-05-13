"""
Send Email lambda function.

This function sends the generated wellness plan PDF to the client via email.
It retrieves the PDF from S3 and sends it as an attachment using AWS SES.
"""

import json
import os
import logging
import sys
import boto3
import io
import time
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client('s3')

def get_pdf_from_s3(bucket: str, key: str) -> bytes:
    """
    Retrieve a PDF file from S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        PDF file as bytes
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_data = response['Body'].read()
        return pdf_data
    except Exception as e:
        logger.error(f"Error retrieving PDF from S3: {str(e)}")
        raise

def create_text_email(client_name):
    """
    Create the plain text version of the email.
    
    Args:
        client_name: Name of the client
        
    Returns:
        String containing the text email body
    """
    return f"""Hello {client_name},

Thank you for choosing our wellness planning service. Your personalized wellness and diet plan is attached to this email.

This plan has been tailored to your specific needs, goals, and preferences. It includes:

1. A comprehensive 4-week meal plan
2. Weekly daily routine recommendations
3. Weekly grocery lists
4. DOs and DON'Ts for your wellness journey
5. Stress management and balance tips
6. Summary and follow-up recommendations

If you have any questions or need adjustments to your plan, please don't hesitate to contact us.

Best regards,
Your Wellness Team
"""

def create_html_email(client_name):
    """
    Create the HTML version of the email.
    
    Args:
        client_name: Name of the client
        
    Returns:
        String containing the HTML email body
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
        }}
        .header {{
            color: #4CAF50;
            border-bottom: 1px solid #4CAF50;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #2E7D32;
            font-size: 24px;
        }}
        h2 {{
            color: #388E3C;
            font-size: 20px;
        }}
        ul {{
            margin-top: 10px;
            margin-bottom: 20px;
        }}
        li {{
            margin-bottom: 5px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #4CAF50;
            font-size: 12px;
            color: #777;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Your Personalized Wellness Plan</h1>
    </div>
    
    <p>Hello {client_name},</p>
    
    <p>Thank you for choosing our wellness planning service. Your personalized wellness and diet plan is attached to this email.</p>
    
    <p>This plan has been tailored to your specific needs, goals, and preferences. It includes:</p>
    
    <ul>
        <li><strong>A comprehensive 4-week meal plan</strong> with easy-to-prepare, nutritious meals</li>
        <li><strong>Weekly daily routine recommendations</strong> to optimize your wellness</li>
        <li><strong>Weekly grocery lists</strong> with all necessary ingredients</li>
        <li><strong>DOs and DON'Ts</strong> for your wellness journey</li>
        <li><strong>Stress management and balance tips</strong> personalized for your lifestyle</li>
        <li><strong>Summary and follow-up recommendations</strong> for continued success</li>
    </ul>
    
    <p>If you have any questions or need adjustments to your plan, please don't hesitate to contact us.</p>
    
    <p>Best regards,<br>
    Your Wellness Team</p>
    
    <div class="footer">
        <p>This email and attachment contain personalized health information intended only for the recipient.</p>
    </div>
</body>
</html>
"""

def extract_parameters(event):
    """
    Extract parameters from the event, handling different input formats.
    
    Args:
        event: The Lambda event object
        
    Returns:
        Tuple of (job_id, pdf_key, pdf_filename, client_data)
    """
    logger.info(f"Extracting parameters from event: {json.dumps(event)}")
    
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
                
            job_id = body.get('job_id')
            pdf_key = body.get('pdf_key')
            pdf_filename = body.get('pdf_filename')
            client_data = body.get('client_data', {})
            
            return job_id, pdf_key, pdf_filename, client_data
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing event body: {str(e)}")
            # Try direct access as fallback
            pass
    
    # Direct event access (direct Lambda invocation)
    job_id = event.get('job_id')
    pdf_key = event.get('pdf_key')
    pdf_filename = event.get('pdf_filename')
    client_data = event.get('client_data', {})
    
    return job_id, pdf_key, pdf_filename, client_data

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: Dict containing job_id, pdf_key, pdf_filename, and client_data
        context: Lambda context
        
    Returns:
        Response with status
    """
    try:
        logger.info(f"Received send email event: {json.dumps(event)}")
        start_time = time.time()
        
        # Extract parameters using the helper function
        job_id, pdf_key, pdf_filename, client_data = extract_parameters(event)
        
        # Validate parameters
        if not job_id or not pdf_key or not pdf_filename or not client_data:
            missing_params = []
            if not job_id: missing_params.append('job_id')
            if not pdf_key: missing_params.append('pdf_key')
            if not pdf_filename: missing_params.append('pdf_filename')
            if not client_data: missing_params.append('client_data')
            
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Extract client info
        client_name = client_data.get('Full Name', 'Client')
        client_email = client_data.get('Email')
        
        if not client_email:
            error_msg = "Client email not provided in client data"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.info(f"Sending wellness plan to {client_name} at {client_email}")
        
        # Check if SES is in sandbox mode by checking sending quota
        ses_client = boto3.client('ses')
        try:
            quota = ses_client.get_send_quota()
            max_send_rate = quota.get('MaxSendRate')
            
            # If max send rate is 1 or less, we're likely in sandbox mode
            is_sandbox = max_send_rate <= 1
            logger.info(f"SES account status: {'SANDBOX' if is_sandbox else 'PRODUCTION'}")
            
            if is_sandbox and not (client_email.endswith('@simulator.amazonses.com') or 
                                   'desaiaditya2710@gmail.com' in client_email):
                logger.warning(
                    f"Account is in SANDBOX mode. Both sender and recipient email addresses must be verified. "
                    f"Recipient: {client_email}"
                )
                
                # Check if the recipient email is verified
                verified_addresses = ses_client.list_verified_email_addresses()
                verified_list = verified_addresses.get('VerifiedEmailAddresses', [])
                
                if client_email not in verified_list:
                    logger.warning(f"Recipient email {client_email} is not verified. Attempting to verify...")
                    # Send verification email
                    ses_client.verify_email_identity(EmailAddress=client_email)
                    logger.info(f"Verification email sent to {client_email}. User must click the link to verify.")
                    return {
                        'statusCode': 202,
                        'body': json.dumps({
                            'job_id': job_id,
                            'status': 'Email verification required',
                            'message': f"Recipient {client_email} is not verified. Verification email has been sent. "
                                      f"Please check the inbox and verify the address before retrying."
                        })
                    }
        except Exception as e:
            logger.warning(f"Could not check SES account status: {str(e)}")
            
        # Download PDF from S3
        logger.info(f"Downloading PDF from S3: {pdf_key}")
        s3_client = boto3.client('s3')
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            pdf_path = temp_file.name
            s3_client.download_fileobj(utils.OUTPUT_BUCKET, pdf_key, temp_file)
        
        # Prepare email
        logger.info("Preparing email")
        ses_client = boto3.client('ses')
        
        # Always use the verified sender email to avoid MessageRejected errors
        sender_email = 'desaiaditya2710@gmail.com'
        logger.info(f"Using verified sender email: {sender_email}")
        
        # Create email subject
        subject = f"Your Personalized Wellness Plan - {client_name}"
        
        # Create email body
        text_body = create_text_email(client_name)
        html_body = create_html_email(client_name)
        
        # Create raw email message
        logger.info("Creating raw email message")
        message = MIMEMultipart('mixed')
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = client_email
        
        # Create the multipart/alternative part
        msg_body = MIMEMultipart('alternative')
        
        # Add text and HTML versions to the message body
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg_body.attach(part1)
        msg_body.attach(part2)
        
        # Attach the message body to the main message
        message.attach(msg_body)
        
        # Add the PDF attachment
        logger.info(f"Attaching PDF: {pdf_filename}")
        with open(pdf_path, 'rb') as file:
            attachment = MIMEApplication(file.read())
            attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            message.attach(attachment)
        
        # Send the email
        logger.info(f"Sending email to {client_email}")
        response = ses_client.send_raw_email(
            Source=sender_email,
            Destinations=[client_email],
            RawMessage={'Data': message.as_string()}
        )
        
        # Clean up temporary file
        os.unlink(pdf_path)
        
        message_id = response.get('MessageId', 'Unknown')
        logger.info(f"Email sent successfully. Message ID: {message_id}")
        
        # Log total execution time
        execution_time = time.time() - start_time
        logger.info(f"Email sent in {execution_time:.2f} seconds")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'job_id': job_id,
                'message_id': message_id,
                'recipient': client_email,
                'status': 'Email sent successfully'
            })
        }
    
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to send email',
                'details': str(e)
            })
        } 