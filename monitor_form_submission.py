#!/usr/bin/env python3
"""
Monitoring script for the complete form submission flow.

This script submits a test form to the API and then monitors AWS resources
to track the progress of the wellness plan generation.

Usage:
    python monitor_form_submission.py [api_endpoint]
"""

import sys
import json
import time
import random
import argparse
import boto3
import requests
from datetime import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Monitor form submission flow.')
    parser.add_argument('api_endpoint', nargs='?', 
                      default='https://24hhe95i09.execute-api.us-east-1.amazonaws.com/dev/form-submission',
                      help='API Gateway endpoint URL')
    parser.add_argument('--client-name', type=str, default=None, help='Name of the test client')
    parser.add_argument('--client-email', type=str, default=None, help='Email of the test client')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--use-simulator', action='store_true', help='Use SES mailbox simulator instead of the provided email')
    return parser.parse_args()

def generate_test_data(client_name=None, client_email=None, use_simulator=False):
    """Generate test form data."""
    # Generate random name and email if not provided
    if not client_name:
        name_prefix = ["John", "Jane", "Alex", "Sam", "Taylor", "Morgan", "Casey"]
        name_suffix = ["Smith", "Jones", "Williams", "Brown", "Miller", "Davis"]
        client_name = f"{random.choice(name_prefix)} {random.choice(name_suffix)}"
    
    if not client_email or use_simulator:
        # Use SES mailbox simulator instead of example.com
        client_email = "success@simulator.amazonses.com"
        print(f"Using SES simulator email address: {client_email}")
    else:
        print(f"Using provided email address: {client_email}")
    
    return {
        "Full Name": client_name,
        "Email": client_email,
        "DOB": "1990-01-01",
        "Gender": "Female" if random.random() > 0.5 else "Male",
        "Height": f"{random.randint(150, 190)} cm",
        "Weight": f"{random.randint(50, 90)} kg",
        "Occupation": "Software Engineer",
        "Medical Conditions": "None",
        "Allergies or Sensitivities": "None",
        "Current Medications": "None",
        "Dietary Preference": random.choice(["Vegan", "Vegetarian", "Omnivore", "Pescatarian"]),
        "Meals per Day": str(random.randint(3, 5)),
        "Usual Meal Times (Breakfast)": "8:00 AM",
        "Usual Meal Times (Lunch)": "1:00 PM",
        "Usual Meal Times (Dinner)": "7:00 PM",
        "Cuisine Preference": random.choice(["Mediterranean", "Asian", "Indian", "Mexican"]),
        "Food You Enjoy": "Fresh vegetables, fruits, whole grains, nuts",
        "Foods you Dislike": "Processed foods",
        "Activity Level": random.choice(["Low", "Moderate", "High"]),
        "Current Exercise Routine": "30 minute walk daily",
        "Sleep Pattern": "11pm to 7am",
        "Stress Level": random.choice(["Low", "Moderate", "High"]),
        "Daily Water Intake": f"{random.randint(15, 30) / 10:.1f} liters",
        "Wellness Goals": "Increase energy, improve focus",
        "Weight Management Goal": random.choice(["Lose weight", "Maintain weight", "Gain weight"]),
        "Energy Level Concerns": "Afternoon energy dip",
        "Food Budget": random.choice(["Low", "Medium", "High"]),
        "Available Cooking Time": f"{random.randint(15, 60)} minutes per meal",
        "Household Size": str(random.randint(1, 4)),
        "Previous Diet Plans": "None",
        "Additional Information": "Test submission for monitoring"
    }

def submit_form(api_endpoint, form_data):
    """Submit form data to API Gateway."""
    print(f"\n=== Submitting Form Data to {api_endpoint} ===")
    try:
        headers = {'Content-Type': 'application/json'}
        
        print(f"Client: {form_data['Full Name']} ({form_data['Email']})")
        
        response = requests.post(
            api_endpoint,
            json=form_data,
            headers=headers,
            timeout=30,
            verify=False  # For testing only
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            submission_id = response_data.get('submissionId')
            print(f"Submission ID: {submission_id}")
            return submission_id
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error submitting form: {str(e)}")
        return None

def monitor_job_in_dynamodb(submission_id, region='us-east-1'):
    """Monitor job progress in DynamoDB."""
    if not submission_id:
        print("No submission ID to monitor")
        return
    
    print(f"\n=== Monitoring Job in DynamoDB ===")
    try:
        # Create DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name=region)
        
        # Get the table
        table = dynamodb.Table('hrim-jobs')
        
        # Query for jobs (may be multiple for same submission)
        print("Searching for jobs...")
        
        # Wait for up to 2 minutes for the job to appear
        max_attempts = 24  # 24 * 5 seconds = 2 minutes
        for attempt in range(max_attempts):
            time.sleep(5)
            
            # Scan the table for jobs related to this submission
            # In production you would use a GSI or query with filter expressions
            response = table.scan()
            
            relevant_items = []
            for item in response.get('Items', []):
                if 'client_data_key' in item and submission_id in item['client_data_key']:
                    relevant_items.append(item)
            
            if relevant_items:
                break
                
            print(f"Waiting for job to appear in DynamoDB... ({attempt + 1}/{max_attempts})")
        
        if not relevant_items:
            print("No jobs found for this submission after 2 minutes")
            return
        
        print(f"Found {len(relevant_items)} job(s) for submission {submission_id}")
        
        # Monitor the job status
        job_id = relevant_items[0]['job_id']
        print(f"Monitoring job: {job_id}")
        
        # Monitor for up to 5 minutes
        max_monitoring_attempts = 30  # 30 * 10 seconds = 5 minutes
        for attempt in range(max_monitoring_attempts):
            response = table.get_item(Key={'job_id': job_id})
            
            if 'Item' in response:
                item = response['Item']
                status = item.get('status', 'UNKNOWN')
                created_at = item.get('created_at', 'UNKNOWN')
                updated_at = item.get('updated_at', 'UNKNOWN')
                
                print(f"Job Status: {status} (Created: {created_at}, Updated: {updated_at})")
                
                if status == 'COMPLETED':
                    print("Job completed successfully!")
                    return True
                elif status == 'ERROR':
                    error = item.get('error', 'Unknown error')
                    print(f"Job failed with error: {error}")
                    return False
            
            time.sleep(10)
            print(f"Waiting for job to complete... ({attempt + 1}/{max_monitoring_attempts})")
        
        print("Job monitoring timed out")
        return False
    except Exception as e:
        print(f"Error monitoring job: {str(e)}")
        return False

def main():
    """Main function."""
    args = parse_arguments()
    
    print("=== HRIM Form Submission Monitor ===")
    print(f"API Endpoint: {args.api_endpoint}")
    
    # Generate test data
    form_data = generate_test_data(args.client_name, args.client_email, args.use_simulator)
    
    # Submit the form
    submission_id = submit_form(args.api_endpoint, form_data)
    
    if submission_id:
        # Monitor the job in DynamoDB
        monitor_job_in_dynamodb(submission_id, args.region)
        
        # Inform the user about the email
        print(f"\nThe wellness plan will be emailed to: {form_data['Email']}")
        print("Check your inbox (and spam folder) for the wellness plan email.")
        
        # If using a real email address, remind about verification
        if not form_data['Email'].endswith('@simulator.amazonses.com'):
            print("\nNOTE: If your AWS SES account is in sandbox mode, ensure both the sender")
            print("      and recipient email addresses are verified in SES.")
    
    print("\n=== Monitoring Complete ===")

if __name__ == "__main__":
    # Suppress InsecureRequestWarning for testing
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main() 