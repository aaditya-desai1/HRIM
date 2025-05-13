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
        # Section 1: Email
        'Email': 'Email',
        
        # Section 2: Personal Details
        'Full Name': 'Full Name',
        'DOB': 'Date of Birth',
        'Date of Birth': 'Date of Birth',  # For backward compatibility
        'Gender': 'Gender',
        'WhatsApp Contact Number': 'Phone Number',
        'Phone Number': 'Phone Number',  # For backward compatibility
        'Address': 'Address',
        'City': 'City',
        'PIN': 'PIN Code',
        'State': 'State',
        'Country': 'Country',
        'Occupation': 'Occupation',
        'Marital Status': 'Marital Status',
        
        # Section 3: Demographic and Lifestyle Information
        'Height (in cm)': 'Height',
        'Height': 'Height',  # For backward compatibility
        'Current Weight (in kg)': 'Weight',
        'Weight': 'Weight',  # For backward compatibility
        'Target Weight (if any)': 'Target Weight',
        'Primary Health Goals': 'Wellness Goals',
        
        # Section 4: Medical History
        'Do you have any existing medical conditions?': 'Has Medical Conditions',
        'If yes, please specify medical conditions.': 'Medical Conditions',
        'Medical Conditions': 'Medical Conditions',  # For backward compatibility
        'Are you currently on any medications?': 'On Medications',
        'If yes, please specify medications': 'Current Medications',
        'Current Medications': 'Current Medications',  # For backward compatibility
        'Any allergies (food or otherwise)?': 'Has Allergies',
        'If yes, Please specify allergies.': 'Allergies or Sensitivities',
        'Allergies or Sensitivities': 'Allergies or Sensitivities',  # For backward compatibility
        'Family Medical History: (e.g. diabetes, heart disease)': 'Family Medical History',
        
        # Section 5: Daily Routine & Lifestyle
        'Wake-Up Time': 'Wake-Up Time',
        'Sleep Time': 'Sleep Time',
        'Average Hours of Sleep': 'Sleep Hours',
        'Sleep Pattern': 'Sleep Pattern',  # For backward compatibility
        'Work Schedule': 'Work Schedule',
        'Physical Activity Level': 'Activity Level',
        'Activity Level': 'Activity Level',  # For backward compatibility
        'Exercise Routine (if any)': 'Current Exercise Routine',
        'Current Exercise Routine': 'Current Exercise Routine',  # For backward compatibility
        'Stress Level': 'Stress Level',
        'Screen Time per Day (in Hours)': 'Screen Time',
        
        # Section 6: Dietary Preferences and Habits
        'Dietary Preference': 'Dietary Preference',
        'Any Dietary Restrictions?': 'Has Dietary Restrictions',
        'If yes, Please specify Dietary Restrictions': 'Dietary Restrictions',
        'Meals per Day': 'Meals per Day',
        'Snacking Habit': 'Snacking Habit',
        'Water Intake Per Day (in Liters)': 'Daily Water Intake',
        'Daily Water Intake': 'Daily Water Intake',  # For backward compatibility
        'Consumption of Caffeine (Tea/Coffee) Cups Per Day': 'Caffeine Consumption',
        'Frequency of Eating Out': 'Eating Out Frequency',
        'Usual Meal Times': 'Usual Meal Times',  # For backward compatibility
        'Cuisine Preference': 'Cuisine Preference',  # For backward compatibility
        'Foods You Enjoy': 'Foods You Enjoy',  # For backward compatibility
        'Food You Enjoy': 'Foods You Enjoy',  # For backward compatibility
        'Foods You Dislike': 'Foods You Dislike',  # For backward compatibility
        'Foods you Dislike': 'Foods You Dislike',  # For backward compatibility
        
        # Section 7: Mental and Emotional Well-being
        'How often do you feel stressed?': 'Stress Frequency',
        'Do you practice any relaxation techniques?': 'Uses Relaxation Techniques',
        'If yes, Specify relaxation techniques.': 'Relaxation Techniques',
        'Hobbies and Leisure Activities (Describe)': 'Hobbies',
        
        # Section 8: Additional Information
        'Any specif concerns or goals you would like to address?': 'Specific Concerns',
        'Have you followed any diet or fitness plan before?': 'Previous Plans Experience',
        'If yes, what type and what were the results?': 'Previous Diet Plans',
        'Previous Diet Plans': 'Previous Diet Plans',  # For backward compatibility
        'Food Budget': 'Food Budget',
        'Available Cooking Time': 'Available Cooking Time',  # For backward compatibility
        'Household Size': 'Household Size',  # For backward compatibility
        'Additional Information': 'Additional Information',
        'Health Goals': 'Wellness Goals',  # For backward compatibility
        'Wellness Goals': 'Wellness Goals',  # For backward compatibility
        'Weight Management Goal': 'Weight Management Goal',  # For backward compatibility
        'Energy Level Concerns': 'Energy Level Concerns'  # For backward compatibility
    }
    
    # Process meal times if they come in separate fields (for backward compatibility)
    if ('Usual Meal Times' not in form_data and 
        ('Usual Meal Times (Breakfast)' in form_data or 
         'Usual Meal Times (Lunch)' in form_data or 
         'Usual Meal Times (Dinner)' in form_data)):
        
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