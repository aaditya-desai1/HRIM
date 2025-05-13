"""
Shared utility functions for HRIM lambda functions.
"""

import boto3
import json
import logging
import os
import uuid
import io
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ses_client = boto3.client('ses')

# Define DynamoDB table name
JOB_TABLE_NAME = os.environ.get('JOB_TABLE_NAME', 'hrim-jobs')

# S3 bucket names
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'hrim-input-data')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'hrim-output-data')

# Define job status constants
class JobStatus:
    CREATED = 'CREATED'
    FETCHING_DATA = 'FETCHING_DATA'
    FORMATTING_PROMPT = 'FORMATTING_PROMPT'
    CALLING_AI = 'CALLING_AI'
    GENERATING_PDF = 'GENERATING_PDF'
    UPLOADING_PDF = 'UPLOADING_PDF'
    SENDING_EMAIL = 'SENDING_EMAIL'
    SENDING_WHATSAPP = 'SENDING_WHATSAPP'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


def generate_job_id() -> str:
    """
    Generate a unique job ID.
    
    Returns:
        A unique job ID string
    """
    return str(uuid.uuid4())


def create_job_record(job_id: str, client_data_key: str) -> Dict[str, Any]:
    """
    Create a job record in DynamoDB.
    
    Args:
        job_id: The job ID
        client_data_key: The S3 key for the client data
        
    Returns:
        The job record
    """
    try:
        # Create job record
        job_record = {
            'job_id': job_id,
            'client_data_key': client_data_key,
            'status': JobStatus.CREATED,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Insert into DynamoDB
        table = dynamodb.Table(JOB_TABLE_NAME)
        table.put_item(Item=job_record)
        
        logger.info(f"Created job record: {job_id}")
        
        return job_record
    except Exception as e:
        logger.error(f"Error creating job record: {str(e)}")
        raise


def update_job_status(job_id: str, status: str, error: Optional[str] = None) -> None:
    """
    Update the status of a job in DynamoDB.
    
    Args:
        job_id: The job ID
        status: The new status
        error: Optional error message
    """
    try:
        # Update job status in DynamoDB
        table = dynamodb.Table(JOB_TABLE_NAME)
        
        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_attribute_names = {
            '#status': 'status'
        }
        expression_attribute_values = {
            ':status': status,
            ':updated_at': datetime.now().isoformat()
        }
        
        if error:
            update_expression += ", error = :error"
            expression_attribute_values[':error'] = error
        
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(f"Updated job status: {job_id} -> {status}")
    except Exception as e:
        logger.error(f"Error updating job status: {str(e)}")
        # Don't raise, as this might be a non-critical error


def update_job_record(job_id: str, updates: Dict[str, Any]) -> None:
    """
    Update a job record with multiple fields in DynamoDB.
    
    Args:
        job_id: The job ID
        updates: Dictionary of field/value pairs to update
    """
    try:
        # Skip empty updates
        if not updates:
            return
            
        # Update job record in DynamoDB
        table = dynamodb.Table(JOB_TABLE_NAME)
        
        # Build update expression and attribute values
        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {
            ':updated_at': datetime.now().isoformat()
        }
        
        # Always update the timestamp
        update_expression_parts.append("updated_at = :updated_at")
        
        # Add each field to the update expressions
        for field, value in updates.items():
            placeholder = f":{field.replace('-', '_')}"
            name_placeholder = f"#{field.replace('-', '_')}"
            
            update_expression_parts.append(f"{name_placeholder} = {placeholder}")
            expression_attribute_names[name_placeholder] = field
            expression_attribute_values[placeholder] = value
        
        # Combine all parts
        update_expression = "SET " + ", ".join(update_expression_parts)
        
        # Perform the update
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(f"Updated job record: {job_id} with fields: {', '.join(updates.keys())}")
    except Exception as e:
        logger.error(f"Error updating job record: {str(e)}")
        # Don't raise, as this might be a non-critical error


def get_job_details(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job details from DynamoDB.
    
    Args:
        job_id: The job ID
        
    Returns:
        The job record or None if not found
    """
    try:
        table = dynamodb.Table(JOB_TABLE_NAME)
        
        response = table.get_item(
            Key={'job_id': job_id}
        )
        
        if 'Item' in response:
            return response['Item']
        else:
            logger.warning(f"Job not found: {job_id}")
            return None
    except Exception as e:
        logger.error(f"Error getting job details: {str(e)}")
        return None


def read_s3_json(bucket: str, key: str) -> Dict[str, Any]:
    """
    Read JSON data from S3.
    
    Args:
        bucket: The S3 bucket name
        key: The S3 object key
        
    Returns:
        The parsed JSON data
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read().decode('utf-8')
        return json.loads(data)
    except Exception as e:
        logger.error(f"Error reading S3 JSON: {str(e)}")
        raise


def write_to_s3(bucket: str, key: str, data: str, content_type: str = 'application/json') -> None:
    """
    Write data to S3.
    
    Args:
        bucket: The S3 bucket name
        key: The S3 object key
        data: The data to write
        content_type: The content type
    """
    try:
        s3_client.put_object(
            Body=data,
            Bucket=bucket,
            Key=key,
            ContentType=content_type
        )
        logger.info(f"Wrote data to S3: {bucket}/{key}")
    except Exception as e:
        logger.error(f"Error writing to S3: {str(e)}")
        raise


def upload_binary_to_s3(bucket: str, key: str, data: bytes, content_type: str) -> None:
    """
    Upload binary data to S3.
    
    Args:
        bucket: The S3 bucket name
        key: The S3 object key
        data: The binary data to upload
        content_type: The content type
    """
    try:
        file_obj = io.BytesIO(data)
        s3_client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs={'ContentType': content_type}
        )
        logger.info(f"Uploaded binary data to S3: {bucket}/{key}")
    except Exception as e:
        logger.error(f"Error uploading binary to S3: {str(e)}")
        raise


def send_email_with_attachment(
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
    pdf_data: bytes,
    attachment_name: str
) -> Tuple[bool, Optional[str]]:
    """
    Send an email with a PDF attachment using SES.
    
    Args:
        recipient: The recipient email address
        subject: The email subject
        text_body: The plain text email body
        html_body: The HTML email body
        pdf_data: The PDF data as bytes
        attachment_name: The name of the attachment
        
    Returns:
        A tuple containing (success, message_id)
    """
    try:
        # Get sender email from environment variable
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@example.com')
        
        # Create a multipart email
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Date'] = email.utils.formatdate(localtime=True)
        
        # Create alternative part for plain text and HTML
        msg_alt = MIMEMultipart('alternative')
        
        # Add plain text part
        text_part = MIMEText(text_body, 'plain', 'utf-8')
        msg_alt.attach(text_part)
        
        # Add HTML part
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg_alt.attach(html_part)
        
        # Add the alternative part to the main message
        msg.attach(msg_alt)
        
        # Add the PDF attachment
        attachment = MIMEApplication(pdf_data)
        attachment.add_header('Content-Disposition', 'attachment', filename=attachment_name)
        msg.attach(attachment)
        
        # Create raw email
        raw_email = msg.as_string().encode('utf-8')
        
        # Send email using SES
        response = ses_client.send_raw_email(
            Source=sender_email,
            Destinations=[recipient],
            RawMessage={'Data': raw_email}
        )
        
        message_id = response.get('MessageId')
        logger.info(f"Email sent to {recipient} with message ID: {message_id}")
        
        return True, message_id
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False, None 