"""
Form submission lambda function.

This function receives form data from API Gateway and stores it in the S3 bucket,
which triggers the HRIM workflow.
"""

import json
import os
import logging
import sys
import time
import boto3
import uuid
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variables
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'hrim-input-data')

# Initialize S3 client
s3_client = boto3.client('s3')

def standardize_form_data(form_data):
    """
    Standardize Google Form data to match the expected format.
    
    Args:
        form_data: Dict containing form submission data
        
    Returns:
        Standardized data dict
    """
    # Create a new dict with standardized keys
    standardized = {}
    
    # Map the incoming form fields to our expected format
    field_mapping = {
        'Full Name': 'Full Name',
        'Email': 'Email',
        'DOB': 'Date of Birth',
        'Gender': 'Gender',
        'Height': 'Height',
        'Weight': 'Weight',
        'Occupation': 'Occupation',
        'Medical Conditions': 'Medical Conditions',
        'Allergies or Sensitivities': 'Allergies or Sensitivities',
        'Current Medications': 'Current Medications',
        'Dietary Preference': 'Dietary Preference',
        'Meals per Day': 'Meals per Day',
        'Cuisine Preference': 'Cuisine Preference',
        'Food You Enjoy': 'Foods You Enjoy',
        'Foods you Dislike': 'Foods You Dislike',
        'Activity Level': 'Activity Level',
        'Current Exercise Routine': 'Current Exercise Routine',
        'Sleep Pattern': 'Sleep Pattern',
        'Stress Level': 'Stress Level',
        'Daily Water Intake': 'Daily Water Intake',
        'Wellness Goals': 'Wellness Goals',
        'Weight Management Goal': 'Weight Management Goal',
        'Energy Level Concerns': 'Energy Level Concerns',
        'Food Budget': 'Food Budget',
        'Available Cooking Time': 'Available Cooking Time',
        'Household Size': 'Household Size',
        'Previous Diet Plans': 'Previous Diet Plans',
        'Additional Information': 'Additional Information'
    }
    
    # Process meal times
    meal_times = []
    if 'Usual Meal Times (Breakfast)' in form_data:
        meal_times.append(f"Breakfast {form_data['Usual Meal Times (Breakfast)']}")
    if 'Usual Meal Times (Lunch)' in form_data:
        meal_times.append(f"Lunch {form_data['Usual Meal Times (Lunch)']}")
    if 'Usual Meal Times (Dinner)' in form_data:
        meal_times.append(f"Dinner {form_data['Usual Meal Times (Dinner)']}")
    
    # Add combined meal times
    if meal_times:
        standardized['Usual Meal Times'] = ', '.join(meal_times)
    
    # Map fields according to our mapping
    for form_key, std_key in field_mapping.items():
        if form_key in form_data:
            standardized[std_key] = form_data[form_key]
    
    # Ensure all required fields are present
    required_fields = [
        'Full Name', 
        'Email',
        'Height',
        'Weight',
        'Wellness Goals'
    ]
    
    for field in required_fields:
        if field not in standardized:
            standardized[field] = "Not provided"
    
    return standardized

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict containing form data
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Received form submission event: {json.dumps(event)}")
        logger.info(f"Environment variables: INPUT_BUCKET={INPUT_BUCKET}")
        
        # Parse the request body
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        logger.info(f"Extracted form data: {json.dumps(body)}")
        
        # Standardize the form data
        standardized_data = standardize_form_data(body)
        logger.info(f"Standardized form data: {json.dumps(standardized_data)}")
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        client_name = standardized_data.get('Full Name', 'Unknown').replace(' ', '_')
        filename = f"{client_name}_{timestamp}_{str(uuid.uuid4())[:8]}.json"
        s3_key = f"incoming/{filename}"
        
        # Store the data in S3
        logger.info(f"Storing form data in S3: {s3_key}")
        logger.info(f"Using S3 bucket: {INPUT_BUCKET}")
        
        # Explicitly create S3 client with default region
        s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        
        s3_client.put_object(
            Body=json.dumps(standardized_data),
            Bucket=INPUT_BUCKET,
            Key=s3_key,
            ContentType='application/json'
        )
        
        logger.info(f"Form data stored successfully in S3: {s3_key}")
        
        # Return success response with CORS headers
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Form data received and processing started',
                'submissionId': filename
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            }
        }
    
    except Exception as e:
        logger.error(f"Error processing form submission: {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Python version: {sys.version}")
        logger.error(f"Available environment variables: {dict(os.environ)}")
        
        # Return error response with CORS headers
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process the form submission',
                'details': str(e),
                'errorType': type(e).__name__
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            }
        } 