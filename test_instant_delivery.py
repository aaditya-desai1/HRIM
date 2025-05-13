#!/usr/bin/env python3
"""
Test script for instant email delivery of wellness plans.

This script tests the complete flow from form submission to email delivery,
measuring the time it takes to generate and deliver the wellness plan.

Usage:
    python test_instant_delivery.py your-email@example.com
"""

import os
import sys
import time
import json
import logging
import argparse
import importlib.util
import uuid
from datetime import datetime
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_instant_delivery')

# Import the test_hrim module for its mock services
from test_hrim import mock_s3, mock_dynamodb, mock_ses

def load_module(module_path, module_name):
    """Load a Python module dynamically."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test instant email delivery of wellness plans.')
    parser.add_argument('email', nargs='?', default='quick-test@example.com', help='Email address to send the wellness plan to')
    parser.add_argument('--client-name', type=str, default='Quick Test User', help='Name of the test client')
    return parser.parse_args()

def generate_form_data(client_name, email):
    """Generate test form data."""
    form_data = {
        "Full Name": client_name,
        "Email": email,
        "DOB": "1985-05-15",
        "Gender": "Male",
        "Height": "175 cm",
        "Weight": "70 kg",
        "Occupation": "Software Developer",
        "Medical Conditions": "None",
        "Allergies or Sensitivities": "None",
        "Current Medications": "None",
        "Dietary Preference": "Vegetarian",
        "Meals per Day": "3",
        "Usual Meal Times (Breakfast)": "7:30 AM",
        "Usual Meal Times (Lunch)": "12:30 PM",
        "Usual Meal Times (Dinner)": "7:00 PM",
        "Cuisine Preference": "Mediterranean",
        "Food You Enjoy": "Fresh vegetables, pasta, olive oil, nuts",
        "Foods you Dislike": "Processed foods",
        "Activity Level": "Moderate",
        "Current Exercise Routine": "Walking 30 minutes daily",
        "Sleep Pattern": "10:30pm to 6:30am",
        "Stress Level": "Low",
        "Daily Water Intake": "2.5 liters",
        "Wellness Goals": "Increase energy, improve focus",
        "Weight Management Goal": "Maintain current weight",
        "Energy Level Concerns": "Afternoon energy dip",
        "Food Budget": "Medium",
        "Available Cooking Time": "30 minutes per meal",
        "Household Size": "2",
        "Previous Diet Plans": "None",
        "Additional Information": "Quick test for faster email delivery."
    }
    return form_data

def test_instant_delivery():
    """
    Run the complete integration test with timing.
    
    1. Submit form data
    2. Process the submission
    3. Generate the wellness plan
    4. Send the email
    5. Measure and report the total time
    """
    start_time = time.time()
    
    # Parse arguments
    args = parse_arguments()
    
    logger.info(f"Starting instant delivery test with email: {args.email}")
    
    # Set up required environment variables
    os.environ['JOB_TABLE_NAME'] = 'hrim-jobs-local'
    os.environ['INPUT_BUCKET'] = 'hrim-input-data-local'
    os.environ['OUTPUT_BUCKET'] = 'hrim-output-data-local'
    os.environ['SENDER_EMAIL'] = 'wellness@hrim.example.com'
    
    # Create output directories
    os.makedirs('test_output', exist_ok=True)
    os.makedirs('test_output/hrim-input-data-local/incoming', exist_ok=True)
    os.makedirs('test_output/hrim-output-data-local', exist_ok=True)
    os.makedirs('test_output/pdfs', exist_ok=True)

    # Track job progression
    job_id = None
    
    try:
        # Step 1: Generate form data
        logger.info("Step 1: Generating form data")
        form_data = generate_form_data(args.client_name, args.email)
        
        # Step 2: Process form submission
        logger.info("Step 2: Processing form submission")
        form_submission_time = time.time()
        
        api_event = {
            'body': json.dumps(form_data)
        }
        
        form_lambda_path = os.path.join('src', 'lambda', 'form_submission', 'lambda_function.py')
        form_lambda = load_module(form_lambda_path, 'form_submission_lambda')
        
        form_response = form_lambda.lambda_handler(api_event, None)
        
        if form_response['statusCode'] != 200:
            logger.error(f"Form submission failed: {form_response['body']}")
            return False
        
        form_response_body = json.loads(form_response['body'])
        submission_id = form_response_body.get('submissionId')
        
        logger.info(f"Form submission processed in {time.time() - form_submission_time:.2f} seconds")
        logger.info(f"Submission ID: {submission_id}")
        
        # Step 3: Trigger workflow
        logger.info("Step 3: Triggering workflow")
        trigger_time = time.time()
        
        s3_key = f"incoming/{submission_id}"
        s3_event = {
            'Records': [
                {
                    'eventSource': 'aws:s3',
                    'eventTime': datetime.now().isoformat(),
                    's3': {
                        'bucket': {
                            'name': os.environ['INPUT_BUCKET']
                        },
                        'object': {
                            'key': s3_key
                        }
                    }
                }
            ]
        }
        
        trigger_lambda_path = os.path.join('src', 'lambda', 'trigger_processor', 'lambda_function.py')
        trigger_lambda = load_module(trigger_lambda_path, 'trigger_processor_lambda')
        
        trigger_response = trigger_lambda.lambda_handler(s3_event, None)
        
        if trigger_response['statusCode'] != 200:
            logger.error(f"Trigger failed: {trigger_response['body']}")
            return False
        
        trigger_response_json = json.loads(trigger_response['body'])
        job_id = trigger_response_json['jobs'][0]['job_id']
        
        logger.info(f"Workflow triggered in {time.time() - trigger_time:.2f} seconds")
        logger.info(f"Job ID: {job_id}")
        
        # Step 4: Process data
        logger.info("Step 4: Fetching client data")
        fetch_time = time.time()
        
        fetch_event = {
            'job_id': job_id,
            'client_data_key': s3_key
        }
        
        fetch_lambda_path = os.path.join('src', 'lambda', 'fetch_data', 'lambda_function.py')
        fetch_lambda = load_module(fetch_lambda_path, 'fetch_data_lambda')
        
        fetch_response = fetch_lambda.lambda_handler(fetch_event, None)
        
        if fetch_response['statusCode'] != 200:
            logger.error(f"Fetch data failed: {fetch_response['body']}")
            return False
        
        logger.info(f"Client data fetched in {time.time() - fetch_time:.2f} seconds")
        
        # Step 5: Format prompt
        logger.info("Step 5: Formatting prompt")
        format_time = time.time()
        
        format_event = {
            'job_id': job_id,
            'client_data': form_data
        }
        
        format_lambda_path = os.path.join('src', 'lambda', 'format_prompt', 'lambda_function.py')
        format_lambda = load_module(format_lambda_path, 'format_prompt_lambda')
        
        format_response = format_lambda.lambda_handler(format_event, None)
        
        if format_response['statusCode'] != 200:
            logger.error(f"Format prompt failed: {format_response['body']}")
            return False
        
        format_response_json = json.loads(format_response['body'])
        prompt = format_response_json.get('prompt')
        
        logger.info(f"Prompt formatted in {time.time() - format_time:.2f} seconds")
        
        # Step 6: Call Gemini
        logger.info("Step 6: Calling Gemini API")
        gemini_time = time.time()
        
        gemini_event = {
            'job_id': job_id,
            'prompt': prompt,
            'client_data': form_data
        }
        
        gemini_lambda_path = os.path.join('src', 'lambda', 'call_gemini', 'lambda_function.py')
        gemini_lambda = load_module(gemini_lambda_path, 'call_gemini_lambda')
        
        gemini_response = gemini_lambda.lambda_handler(gemini_event, None)
        
        if gemini_response['statusCode'] != 200:
            logger.error(f"Gemini call failed: {gemini_response['body']}")
            return False
        
        gemini_response_json = json.loads(gemini_response['body'])
        ai_response = gemini_response_json.get('response')
        
        logger.info(f"Gemini API response received in {time.time() - gemini_time:.2f} seconds")
        
        # Step 7: Generate PDF
        logger.info("Step 7: Generating PDF")
        pdf_time = time.time()
        
        pdf_event = {
            'job_id': job_id,
            'response': ai_response,
            'client_data': form_data
        }
        
        pdf_lambda_path = os.path.join('src', 'lambda', 'generate_pdf', 'lambda_function.py')
        pdf_lambda = load_module(pdf_lambda_path, 'generate_pdf_lambda')
        
        pdf_response = pdf_lambda.lambda_handler(pdf_event, None)
        
        if pdf_response['statusCode'] != 200:
            logger.error(f"PDF generation failed: {pdf_response['body']}")
            return False
        
        pdf_response_json = json.loads(pdf_response['body'])
        pdf_key = pdf_response_json.get('pdf_key')
        pdf_filename = pdf_response_json.get('pdf_filename')
        
        logger.info(f"PDF generated in {time.time() - pdf_time:.2f} seconds")
        logger.info(f"PDF filename: {pdf_filename}")
        
        # Step 8: Upload PDF
        logger.info("Step 8: Uploading PDF")
        upload_time = time.time()
        
        upload_event = {
            'job_id': job_id,
            'pdf_key': pdf_key,
            'pdf_filename': pdf_filename,
            'client_data': form_data
        }
        
        upload_lambda_path = os.path.join('src', 'lambda', 'upload_pdf', 'lambda_function.py')
        upload_lambda = load_module(upload_lambda_path, 'upload_pdf_lambda')
        
        upload_response = upload_lambda.lambda_handler(upload_event, None)
        
        if upload_response['statusCode'] != 200:
            logger.error(f"PDF upload failed: {upload_response['body']}")
            return False
        
        logger.info(f"PDF uploaded in {time.time() - upload_time:.2f} seconds")
        
        # Step 9: Send Email
        logger.info("Step 9: Sending email")
        email_time = time.time()
        
        email_event = {
            'job_id': job_id,
            'pdf_key': pdf_key,
            'pdf_filename': pdf_filename,
            'client_data': form_data
        }
        
        email_lambda_path = os.path.join('src', 'lambda', 'send_email', 'lambda_function.py')
        email_lambda = load_module(email_lambda_path, 'send_email_lambda')
        
        email_response = email_lambda.lambda_handler(email_event, None)
        
        if email_response['statusCode'] != 200:
            logger.error(f"Email sending failed: {email_response['body']}")
            return False
        
        email_response_json = json.loads(email_response['body'])
        message_id = email_response_json.get('message_id')
        
        logger.info(f"Email sent in {time.time() - email_time:.2f} seconds")
        logger.info(f"Message ID: {message_id}")
        
        # Step 10: Complete job
        logger.info("Step 10: Completing job")
        complete_time = time.time()
        
        complete_event = {
            'job_id': job_id
        }
        
        complete_lambda_path = os.path.join('src', 'lambda', 'complete_job', 'lambda_function.py')
        complete_lambda = load_module(complete_lambda_path, 'complete_job_lambda')
        
        complete_response = complete_lambda.lambda_handler(complete_event, None)
        
        if complete_response['statusCode'] != 200:
            logger.error(f"Job completion failed: {complete_response['body']}")
            return False
        
        logger.info(f"Job completed in {time.time() - complete_time:.2f} seconds")
        
        # Calculate and report total time
        total_time = time.time() - start_time
        logger.info(f"TOTAL TIME: {total_time:.2f} seconds")
        
        # Verify email was sent
        if mock_ses.emails:
            logger.info(f"Mock email details:")
            for i, email in enumerate(mock_ses.emails):
                logger.info(f"Email {i+1}:")
                if 'source' in email:
                    logger.info(f"  From: {email['source']}")
                if 'destinations' in email and email['destinations']:
                    logger.info(f"  To: {', '.join(email['destinations'])}")
                
            logger.info(f"SUCCESS: Wellness plan delivered to {args.email} in {total_time:.2f} seconds!")
            return True
        else:
            logger.error("No emails were sent during the test.")
            return False
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        
        # Try to clean up job if something went wrong
        if job_id:
            try:
                job_table = mock_dynamodb.Table(os.environ['JOB_TABLE_NAME'])
                job_table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression="SET status = :status, error = :error",
                    ExpressionAttributeValues={
                        ':status': 'ERROR',
                        ':error': str(e)
                    }
                )
            except Exception as update_error:
                logger.error(f"Failed to update job status: {str(update_error)}")
                
        return False

if __name__ == "__main__":
    success = test_instant_delivery()
    sys.exit(0 if success else 1) 