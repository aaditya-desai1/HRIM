#!/usr/bin/env python3
"""
Integration test for Google Form submission and HRIM workflow.

This script:
1. Simulates a Google Form submission
2. Triggers the form_submission Lambda function directly
3. Verifies that the data is stored in S3
4. Checks that the HRIM workflow is triggered

Usage:
    python test_form_integration.py [--email your-email@example.com]
"""

import os
import sys
import json
import logging
import argparse
import importlib.util
import uuid
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_form_integration')

# Import the test_hrim module for its mock services
from test_hrim import mock_s3, mock_dynamodb

def load_module(module_path, module_name):
    """Load a Python module dynamically."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test Google Form submission integration with HRIM.')
    parser.add_argument('--email', type=str, help='Email address to use for the test')
    parser.add_argument('--client-name', type=str, default='Integration Test User', help='Name of the test client')
    return parser.parse_args()

def generate_form_data(client_name, email=None):
    """Generate test form data."""
    form_data = {
        "Full Name": client_name,
        "Email": email or f"test-{str(uuid.uuid4())[:8]}@example.com",
        "DOB": "1985-05-15",
        "Gender": "Male",
        "Height": "175 cm",
        "Weight": "70 kg",
        "Occupation": "Software Developer",
        "Medical Conditions": "None",
        "Allergies or Sensitivities": "Dairy",
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
        "Current Exercise Routine": "Walking 30 minutes daily, weight training twice a week",
        "Sleep Pattern": "10:30pm to 6:30am",
        "Stress Level": "Moderate",
        "Daily Water Intake": "2.5 liters",
        "Wellness Goals": "Increase energy, maintain muscle mass, improve focus",
        "Weight Management Goal": "Maintain current weight",
        "Energy Level Concerns": "Afternoon energy dip around 3pm",
        "Food Budget": "Medium",
        "Available Cooking Time": "45 minutes per meal, meal prep on weekends",
        "Household Size": "2",
        "Previous Diet Plans": "None",
        "Additional Information": "I work remotely and spend most of the day sitting. Looking for ways to incorporate more movement and healthier eating habits during work hours."
    }
    return form_data

def test_form_submission():
    """
    Run the complete integration test.
    
    1. Generate mock form data
    2. Call the form_submission Lambda directly
    3. Verify the data is stored in S3 and workflow is triggered
    """
    # Parse arguments
    args = parse_arguments()
    
    logger.info(f"Starting integration test with client: {args.client_name}")
    
    # Set up required environment variables
    os.environ['JOB_TABLE_NAME'] = 'hrim-jobs-local'
    os.environ['INPUT_BUCKET'] = 'hrim-input-data-local'
    os.environ['OUTPUT_BUCKET'] = 'hrim-output-data-local'

    # Create output directories
    os.makedirs('test_output', exist_ok=True)
    os.makedirs('test_output/hrim-input-data-local', exist_ok=True)
    os.makedirs('test_output/hrim-input-data-local/incoming', exist_ok=True)
    
    # Generate form data
    form_data = generate_form_data(args.client_name, args.email)
    logger.info(f"Generated form data for client: {form_data['Full Name']}")
    
    # Prepare API Gateway event
    api_event = {
        'body': json.dumps(form_data)
    }
    
    # Load and call the form_submission Lambda function
    try:
        logger.info("Calling form_submission Lambda function")
        form_lambda_path = os.path.join('src', 'lambda', 'form_submission', 'lambda_function.py')
        form_lambda = load_module(form_lambda_path, 'form_submission_lambda')
        
        response = form_lambda.lambda_handler(api_event, None)
        
        logger.info(f"Form submission Lambda response: {json.dumps(response, indent=2)}")
        
        if response['statusCode'] != 200:
            logger.error(f"Form submission failed: {response['body']}")
            return False
        
        # Extract the submission ID from the response
        response_body = json.loads(response['body'])
        submission_id = response_body.get('submissionId')
        
        if not submission_id:
            logger.error("No submission ID in the response")
            return False
        
        logger.info(f"Form data saved with ID: {submission_id}")
        
        # Verify the file was saved in S3
        s3_key = f"incoming/{submission_id}"
        try:
            # Check if we can find the file in the mock S3
            s3_path = f"test_output/hrim-input-data-local/{s3_key}"
            if os.path.exists(s3_path):
                logger.info(f"Verified form data saved to S3: {s3_path}")
                
                # Display the content of the saved file
                with open(s3_path, 'r') as f:
                    saved_data = json.load(f)
                logger.info(f"Saved data: {json.dumps(saved_data, indent=2)}")
                
                # Now simulate the trigger_processor Lambda
                logger.info("Simulating S3 event to trigger the workflow")
                
                # Create a mock S3 event
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
                
                # Load and call the trigger_processor Lambda
                trigger_lambda_path = os.path.join('src', 'lambda', 'trigger_processor', 'lambda_function.py')
                trigger_lambda = load_module(trigger_lambda_path, 'trigger_processor_lambda')
                
                trigger_response = trigger_lambda.lambda_handler(s3_event, None)
                
                logger.info(f"Trigger processor response: {json.dumps(trigger_response, indent=2)}")
                
                if trigger_response['statusCode'] != 200:
                    logger.error(f"Trigger processor failed: {trigger_response['body']}")
                    return False
                
                # Extract job ID from the response
                response_json = json.loads(trigger_response['body'])
                job_id = response_json['jobs'][0]['job_id']
                logger.info(f"Job created with ID: {job_id}")
                
                # Verify the job was created in DynamoDB
                job_table = mock_dynamodb.Table(os.environ['JOB_TABLE_NAME'])
                job_data = job_table.get_item(Key={'job_id': job_id})
                
                if 'Item' in job_data:
                    logger.info(f"Job data in DynamoDB: {json.dumps(job_data['Item'], indent=2)}")
                    logger.info("Integration test completed successfully!")
                    return True
                else:
                    logger.error(f"Job {job_id} not found in DynamoDB")
                    return False
            else:
                logger.error(f"Form data not found in S3: {s3_path}")
                return False
        except Exception as e:
            logger.error(f"Error verifying S3 data: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error during integration test: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_form_submission()
    sys.exit(0 if success else 1) 