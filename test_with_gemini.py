#!/usr/bin/env python3
"""
Test script for HRIM using Google's Gemini 2.0 API and AWS SES for real email delivery.

This script provides an integrated test with:
- Real Gemini API calls instead of OpenAI
- Real email delivery through AWS SES
- No WhatsApp integration
- No wait time (immediate delivery)
"""

import json
import os
import sys
import logging
import uuid
import boto3
import requests
from datetime import datetime
import io
import xhtml2pdf.pisa as pisa
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import email.utils
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_with_gemini')

# Configure AWS credentials
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
boto3.setup_default_session(region_name='us-east-1')

# Gemini API key
GEMINI_API_KEY = "AIzaSyAYS1tFe_PDyoAQBsRHdQIWuQIrwgr2Q1w"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

def create_output_directories():
    """Create directories for test outputs."""
    dirs = [
        'test_output',
        'test_output/pdfs',
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def load_test_data():
    """Load test data from the test-data directory."""
    test_data_file = os.path.join('test-data', 'sample-form-submission.json')
    
    if not os.path.exists(test_data_file):
        logger.error(f"Test data file not found: {test_data_file}")
        return None
        
    with open(test_data_file, 'r') as f:
        return json.load(f)

def format_prompt(client_data):
    """Format a prompt for the wellness plan generation."""
    name = client_data.get('Full Name', 'Unknown')
    age = client_data.get('Age', 'Unknown')
    height = client_data.get('Height', 'Unknown')
    weight = client_data.get('Weight', 'Unknown')
    goals = client_data.get('Health Goals', 'Unknown')
    
    prompt = f"""
Please create a comprehensive wellness plan for the following client:

Name: {name}
Age: {age}
Height: {height}
Weight: {weight}
Health Goals: {goals}

The wellness plan should include:
1. A four-week meal plan with specific meals for each day (breakfast, lunch, dinner, snacks)
2. Daily routine recommendations
3. DOs and DON'Ts
4. Summary and follow-up recommendations

Format the output in Markdown and make it well-structured for conversion to PDF.
"""
    return prompt

def call_gemini_api(prompt):
    """Call the Gemini API with the prompt."""
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 4096,
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    logger.info("Calling Gemini API...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Gemini API error: {response.status_code} - {response.text}")
        return f"# Error generating wellness plan\n\nThere was an error with the Gemini API: {response.status_code}"
    
    try:
        response_json = response.json()
        wellness_plan = response_json['candidates'][0]['content']['parts'][0]['text']
        logger.info("Successfully received response from Gemini API")
        return wellness_plan
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing Gemini API response: {e}")
        logger.error(f"Response: {response.text}")
        return "# Error in wellness plan generation\n\nThere was an error processing the API response."

def generate_pdf(wellness_plan, client_name):
    """Generate a PDF from the wellness plan."""
    # Convert markdown to HTML (simple conversion)
    html = "<html><head><style>"
    html += "body { font-family: Arial, sans-serif; margin: 40px; }"
    html += "h1 { color: #2c3e50; }"
    html += "h2 { color: #3498db; margin-top: 20px; }"
    html += "h3 { color: #2980b9; }"
    html += "ul { margin-bottom: 15px; }"
    html += "li { margin-bottom: 5px; }"
    html += "</style></head><body>"
    
    # Simple markdown to HTML conversion
    for line in wellness_plan.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            html += f"<h1>{line[2:]}</h1>"
        elif line.startswith('## '):
            html += f"<h2>{line[3:]}</h2>"
        elif line.startswith('### '):
            html += f"<h3>{line[4:]}</h3>"
        elif line.startswith('- '):
            if not html.endswith('</ul>') and not html.endswith('<ul>'):
                html += "<ul>"
            html += f"<li>{line[2:]}</li>"
        elif line == '' and html.endswith('</li>'):
            html += "</ul>"
        elif line:
            html += f"<p>{line}</p>"
    
    html += "</body></html>"
    
    # Create PDF
    pdf_data = io.BytesIO()
    pisa.CreatePDF(html, dest=pdf_data)
    pdf_data.seek(0)
    
    # Save PDF to file for verification
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{client_name.replace(' ', '_')}_wellness_plan_{timestamp}.pdf"
    pdf_path = os.path.join('test_output', 'pdfs', filename)
    with open(pdf_path, 'wb') as f:
        f.write(pdf_data.read())
    
    pdf_data.seek(0)
    return pdf_data.read(), pdf_path

def send_real_email(client_data, pdf_data, pdf_filename, sender_email):
    """
    Send a real email using AWS SES.
    
    Args:
        client_data (dict): Client information
        pdf_data (bytes): PDF data to attach
        pdf_filename (str): Filename for the PDF attachment
        sender_email (str): Your verified SES email address
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if sender email is provided
        if not sender_email:
            logger.error("No sender email provided. Please provide an email address as argument.")
            logger.info("Example: python3 test_with_gemini.py your-verified-email@example.com")
            return False
        
        # Initialize SES client
        ses = boto3.client('ses')
        
        # Get client info
        client_name = client_data.get('Full Name', 'Valued Client')
        
        # Use sender's email as recipient (to avoid verification issues)
        client_email = sender_email
        logger.info(f"Using sender email as recipient: {client_email}")
        
        # Set up email parameters
        subject = f"Wellness Plan for {client_name} (Test)"
        
        # Create email parts
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = client_email
        msg['Date'] = email.utils.formatdate()
        
        # Create alternative part (text/html)
        alt = MIMEMultipart('alternative')
        
        # Text email body
        text_body = f"""
Hello,

This is a test email containing a personalized wellness plan for {client_name}.
This plan would normally be sent to {client_data.get('Email', 'the client')}, but for testing purposes, it's being sent to your verified email.

Thank you for testing the wellness planning service!
        """
        
        # HTML email body
        html_body = f"""
<html>
<head></head>
<body>
    <p>Hello,</p>
    
    <p>This is a test email containing a personalized wellness plan for <strong>{client_name}</strong>.</p>
    <p>This plan would normally be sent to {client_data.get('Email', 'the client')}, but for testing purposes, it's being sent to your verified email.</p>
    
    <p>Thank you for testing the wellness planning service!</p>
</body>
</html>
        """
        
        # Attach text part
        textpart = MIMEText(text_body.encode('utf-8'), 'plain', 'utf-8')
        alt.attach(textpart)
        
        # Attach HTML part
        htmlpart = MIMEText(html_body.encode('utf-8'), 'html', 'utf-8')
        alt.attach(htmlpart)
        
        # Attach the multipart/alternative child container to the multipart/mixed parent container
        msg.attach(alt)
        
        # Add attachment
        att = MIMEApplication(pdf_data)
        att.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
        msg.attach(att)
        
        # Convert message to string and send
        response = ses.send_raw_email(
            Source=sender_email,
            Destinations=[client_email],
            RawMessage={'Data': msg.as_string()}
        )
        
        logger.info(f"Email sent successfully! Message ID: {response['MessageId']}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def run_integrated_test(email=None):
    """
    Run an integrated test using Gemini API and real email delivery.
    
    Args:
        email (str, optional): Verified email address to use for sender/recipient
    """
    start_time = datetime.now()
    logger.info("Starting integrated test with Gemini API and real email")
    
    # Create output directories
    create_output_directories()
    
    # Load test data
    client_data = load_test_data()
    if not client_data:
        logger.error("Failed to load test data")
        return False
    
    client_name = client_data.get('Full Name', 'Unknown Client')
    logger.info(f"Loaded test data for client: {client_name}")
    
    # Generate job ID for tracking
    job_id = str(uuid.uuid4())
    logger.info(f"Created job ID: {job_id}")
    
    try:
        # Step 1: Format prompt
        logger.info("Step 1: Formatting prompt for wellness plan")
        prompt = format_prompt(client_data)
        
        # Step 2: Call Gemini API
        logger.info("Step 2: Calling Gemini API")
        wellness_plan = call_gemini_api(prompt)
        
        # Step 3: Generate PDF
        logger.info("Step 3: Generating PDF from wellness plan")
        pdf_data, pdf_path = generate_pdf(wellness_plan, client_name)
        logger.info(f"PDF generated and saved to {pdf_path}")
        
        # Step 4: Send real email (if email address provided)
        if email:
            logger.info(f"Step 4: Sending real email to {email}")
            pdf_filename = os.path.basename(pdf_path)
            email_success = send_real_email(client_data, pdf_data, pdf_filename, email)
            
            if email_success:
                logger.info("Email delivery successful")
            else:
                logger.error("Email delivery failed")
        else:
            logger.info("Skipping email delivery (no email address provided)")
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Test completed in {processing_time:.2f} seconds")
        logger.info(f"PDF output is available at: {pdf_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during integrated test: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # Check if email was provided as a command-line argument
    email_arg = None
    if len(sys.argv) > 1:
        email_arg = sys.argv[1]
        logger.info(f"Email provided as argument: {email_arg}")
    else:
        # Try to get from environment variable as fallback
        email_arg = os.environ.get('SENDER_EMAIL')
        if email_arg:
            logger.info(f"Using email from SENDER_EMAIL environment variable: {email_arg}")
        else:
            logger.warning("No email address provided. PDF will be generated but not sent.")
            logger.info("To send email, run: python3 test_with_gemini.py your-verified-email@example.com")
    
    success = run_integrated_test(email=email_arg)
    sys.exit(0 if success else 1) 