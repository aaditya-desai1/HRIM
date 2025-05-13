#!/usr/bin/env python3
"""
Test script for sending an email using real AWS SES service.

This script allows testing the email delivery functionality with real AWS SES
while mocking other external services.
"""

import json
import os
import sys
import logging
import boto3
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import email.utils

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_ses_delivery')

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def load_test_data():
    """Load test data from the test-data directory."""
    test_data_file = os.path.join('test-data', 'sample-form-submission.json')
    
    if not os.path.exists(test_data_file):
        logger.error(f"Test data file not found: {test_data_file}")
        return None
        
    with open(test_data_file, 'r') as f:
        return json.load(f)

def create_output_directories():
    """Create directories for test outputs."""
    dirs = [
        'test_output',
        'test_output/pdfs',
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def simulate_wellness_plan():
    """Simulate generating a wellness plan."""
    # Create a sample wellness plan (abbreviated version)
    return """
# Four-Week Meal Plan

## Week 1 Meal Plan:

### Monday
- **Breakfast**: Masala Oats with Almonds and Fresh Fruits
- **Lunch**: Rajma Chawal with Jeera Raita
- **Dinner**: Roti with Palak Tofu Curry
- **Snack 1**: Chickpea Chaat
- **Snack 2**: Apple with Peanut Butter

## DOs:
- DO include protein-rich foods like lentils, chickpeas, and tofu in every meal
- DO drink at least 8 glasses of water throughout the day
- DO practice mindful eating by chewing slowly and avoiding distractions

## DON'Ts:
- DON'T skip meals, especially breakfast
- DON'T consume caffeine after 2 PM as it may affect sleep quality
- DON'T eat heavy meals within 2 hours of bedtime

## Summary & Follow-up

This personalized wellness plan addresses weight gain, boosting immunity, reducing stress, and improving sleep quality through balanced nutrition and lifestyle modifications.
"""

def generate_sample_pdf(wellness_plan, output_path):
    """Generate a simple text file as a placeholder for a PDF."""
    # In a real implementation, this would create a PDF
    # For testing, we'll just create a text file
    with open(output_path, 'w') as f:
        f.write(wellness_plan)
    logger.info(f"Generated sample output file: {output_path}")
    
    # Return the file data as bytes for email attachment
    with open(output_path, 'rb') as f:
        return f.read()

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

def send_test_email(client_data, pdf_data, pdf_filename):
    """
    Send a test email using AWS SES.
    
    Args:
        client_data (dict): Client information
        pdf_data (bytes): PDF data to attach
        pdf_filename (str): Filename for the PDF attachment
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Initialize SES client
        ses = boto3.client('ses')
        
        # Get client info
        client_name = client_data.get('Full Name', 'Valued Client')
        client_email = client_data.get('Email', None)
        
        if not client_email:
            logger.error("No email address found in client data")
            return False
        
        # Set up email parameters
        sender_email = os.environ.get('SENDER_EMAIL', 'your-verified-email@example.com')
        subject = "Your Personalized Wellness Plan (Test)"
        
        # Create email body
        text_body = f"""
Hello {client_name},

Your personalized wellness plan is attached to this email. This plan has been specifically created for you based on the information you provided.

The plan includes:
- 4-Week Meal Plan
- Weekly Daily Routine Chart
- Weekly Grocery Lists
- DOs & DON'Ts
- Stress & Balance Tips
- Summary & Follow-up Recommendations

This is a test email from the HRIM system.

Thank you for choosing our wellness planning service!
        """
        
        html_body = f"""
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
    
    <p><em>This is a test email from the HRIM system.</em></p>
    
    <p>Thank you for choosing our wellness planning service!</p>
</body>
</html>
        """
        
        # Create raw email
        raw_email = create_raw_email_with_attachment(
            sender=sender_email,
            recipients=[client_email],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            attachment=pdf_data,
            filename=pdf_filename
        )
        
        # Send email
        response = ses.send_raw_email(
            Source=sender_email,
            Destinations=[client_email],
            RawMessage={'Data': raw_email}
        )
        
        logger.info(f"Email sent successfully to {client_email}")
        logger.info(f"SES Message ID: {response.get('MessageId')}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def run_ses_test():
    """Run a test of the AWS SES email delivery."""
    logger.info("Starting SES email delivery test")
    
    # Create output directories
    create_output_directories()
    
    # Load test data
    client_data = load_test_data()
    if not client_data:
        logger.error("Failed to load test data")
        return False
    
    logger.info(f"Loaded test data for client: {client_data.get('Full Name', 'Unknown')}")
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Simulate generating wellness plan
    logger.info("Generating sample wellness plan")
    wellness_plan = simulate_wellness_plan()
    
    # Generate PDF
    logger.info("Creating PDF document")
    client_name = client_data.get('Full Name', 'Unknown Client')
    pdf_filename = f"{client_name.replace(' ', '_')}_wellness_plan_{job_id[:8]}.pdf"
    pdf_path = os.path.join('test_output', 'pdfs', pdf_filename)
    pdf_data = generate_sample_pdf(wellness_plan, pdf_path)
    
    # Check if SENDER_EMAIL is set
    sender_email = os.environ.get('SENDER_EMAIL')
    if not sender_email:
        logger.error("SENDER_EMAIL environment variable not set. Please set it to your verified SES email address.")
        logger.info("Example: export SENDER_EMAIL=your-verified-email@example.com")
        return False
        
    # Send email using SES
    logger.info(f"Sending email to {client_data.get('Email')}")
    result = send_test_email(client_data, pdf_data, pdf_filename)
    
    if result:
        logger.info("SES test completed successfully!")
        return True
    else:
        logger.error("SES test failed")
        return False

if __name__ == "__main__":
    success = run_ses_test()
    sys.exit(0 if success else 1) 