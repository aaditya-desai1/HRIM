#!/usr/bin/env python3
"""
Mixed testing script for the HRIM project.

This script combines real AWS SES for email delivery with mock implementations
for other external services like OpenAI and WhatsApp.
"""

import json
import os
import sys
import logging
import boto3
import uuid
import time
from datetime import datetime
import importlib.util

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_mixed_workflow')

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def setup_environment():
    """Set up environment variables needed for testing."""
    # Set variables for mock implementations
    os.environ['USE_LOCAL_MOCK'] = 'true'
    os.environ['LOCAL_MOCK_FILE'] = 'src/lambda/mocks/mock_responses/wellness_plan.txt'
    os.environ['DEBUG_MODE'] = 'true'
    
    # Check for required environment variables
    sender_email = os.environ.get('SENDER_EMAIL')
    if not sender_email:
        logger.error("SENDER_EMAIL environment variable not set. Please set it to your verified SES email address.")
        logger.info("Example: export SENDER_EMAIL=your-verified-email@example.com")
        return False
        
    return True

def create_test_directories():
    """Create necessary directories for test outputs."""
    dirs = [
        'test_output',
        'test_output/pdfs',
        'src/lambda/mocks/mock_responses',
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def ensure_mock_response_file():
    """Ensure that the mock OpenAI response file exists."""
    mock_file_path = 'src/lambda/mocks/mock_responses/wellness_plan.txt'
    
    if not os.path.exists(mock_file_path):
        logger.info(f"Creating mock response file at {mock_file_path}")
        # Sample wellness plan (abbreviated version)
        mock_response = """# Four-Week Meal Plan

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
        with open(mock_file_path, 'w') as f:
            f.write(mock_response)

def load_test_data():
    """Load test data from the test-data directory."""
    test_data_file = os.path.join('test-data', 'sample-form-submission.json')
    
    if not os.path.exists(test_data_file):
        logger.error(f"Test data file not found: {test_data_file}")
        return None
        
    with open(test_data_file, 'r') as f:
        return json.load(f)

def import_lambda_function(function_name):
    """Dynamically import a Lambda function module."""
    module_path = f'src.lambda.{function_name}.lambda_function'
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        logger.error(f"Failed to import {module_path}: {e}")
        sys.exit(1)

def setup_mock_data():
    """Set up mock test data."""
    # Create a test S3 bucket and key
    test_bucket = "mock-wellness-data-input"
    test_key = f"forms/test-submission-{uuid.uuid4()}.json"
    output_bucket = "mock-wellness-plan-output"
    job_id = str(uuid.uuid4())
    start_time = datetime.utcnow().isoformat()
    
    # Create client data
    client_data = load_test_data()
    if not client_data:
        logger.error("Failed to load test data")
        return None
    
    # Create a simulated job record
    job = {
        'job_id': job_id,
        'input_s3_bucket': test_bucket,
        'input_s3_key': test_key,
        'status': 'PENDING',
        'start_time': start_time,
        'client_email': client_data.get('Email', 'test@example.com'),
        'client_whatsapp': client_data.get('WhatsApp Contact Number', '+1234567890'),
        'client_name': client_data.get('Full Name', 'Test Client'),
    }
    
    return {
        'job': job,
        'client_data': client_data,
        'test_bucket': test_bucket,
        'test_key': test_key,
        'output_bucket': output_bucket
    }

def run_mixed_test():
    """Run a test using real SES for email and mocks for other services."""
    logger.info("Starting mixed workflow test (real SES, mock OpenAI)")
    
    # Set up environment
    if not setup_environment():
        return False
    
    # Create test directories
    create_test_directories()
    
    # Ensure we have a mock OpenAI response file
    ensure_mock_response_file()
    
    # Set up mock data
    test_data = setup_mock_data()
    if not test_data:
        return False
    
    job = test_data['job']
    client_data = test_data['client_data']
    test_bucket = test_data['test_bucket']
    test_key = test_data['test_key']
    output_bucket = test_data['output_bucket']
    job_id = job['job_id']
    
    logger.info(f"Created mock job with ID: {job_id}")
    logger.info(f"Testing with client: {job['client_name']}")
    
    try:
        # Import Lambda functions
        format_prompt = import_lambda_function("format_prompt")
        call_openai = import_lambda_function("call_openai")
        generate_pdf = import_lambda_function("generate_pdf")
        send_email = import_lambda_function("send_email")
        
        # Step 1: Format prompt
        logger.info("Step 1: Format prompt")
        format_event = {
            'job_id': job_id,
            'client_data': client_data
        }
        
        format_result = format_prompt.lambda_handler(format_event, None)
        logger.info("Prompt formatted successfully")
        
        # Step 2: Call OpenAI (will use mock)
        logger.info("Step 2: Call OpenAI (mock)")
        openai_result = call_openai.lambda_handler(format_result, None)
        logger.info("OpenAI API call completed (mock)")
        
        # Step 3: Generate PDF
        logger.info("Step 3: Generate PDF")
        pdf_result = generate_pdf.lambda_handler(openai_result, None)
        logger.info("PDF generation completed")
        
        # The PDF data comes back base64 encoded, save it to a file
        pdf_data = pdf_result.get('pdf_data', '').encode('latin1')
        pdf_filename = f"{job['client_name'].replace(' ', '_')}_wellness_plan_{job_id[:8]}.pdf"
        pdf_path = os.path.join('test_output', 'pdfs', pdf_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)
        logger.info(f"Saved PDF to {pdf_path}")
        
        # Step 4: Set up email sending event
        output_s3_key = f"plans/{job_id}/{pdf_filename}"
        
        # Send email using real SES but with our test parameters
        email_event = {
            'job_id': job_id,
            'output_s3_bucket': output_bucket,
            'output_s3_key': output_s3_key,
            'pdf_data': pdf_result.get('pdf_data'),
            # Optional: override recipient for testing
            'test_recipient': os.environ.get('TEST_RECIPIENT', client_data.get('Email'))
        }
        
        # Need to monkey patch the S3 client in the send_email function to return our PDF data
        original_get_object = boto3.client('s3').get_object
        
        # Mock S3 get_object to return our PDF data
        def mock_get_object(**kwargs):
            return {
                'Body': type('obj', (object,), {
                    'read': lambda: pdf_data
                })
            }
        
        # Apply monkey patch
        boto3.client('s3').get_object = mock_get_object
        
        try:
            # Step 5: Send Email (using real SES)
            logger.info("Step 5: Send Email (using real SES)")
            email_result = send_email.lambda_handler(email_event, None)
            logger.info(f"Email delivery result: {json.dumps(email_result)}")
            
            if email_result.get('email_status') == 'SUCCESS':
                logger.info(f"Email sent successfully! SES Message ID: {email_result.get('email_message_id')}")
            else:
                logger.error(f"Email delivery failed: {email_result.get('error', 'Unknown error')}")
        finally:
            # Restore original S3 client
            boto3.client('s3').get_object = original_get_object
        
        logger.info("Mixed workflow test completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = run_mixed_test()
    sys.exit(0 if success else 1) 