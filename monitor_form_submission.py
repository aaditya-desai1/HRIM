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
import os
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
    
    # Always set sender email for all tests
    os.environ['SENDER_EMAIL'] = 'desaiaditya2710@gmail.com'
    print(f"Setting sender email to: {os.environ['SENDER_EMAIL']}")
    
    if not client_email or use_simulator:
        # Use SES mailbox simulator instead of example.com
        client_email = "success@simulator.amazonses.com"
        print(f"Using SES simulator email address: {client_email}")
    else:
        print(f"Using provided email address: {client_email}")
    
    return {
        # SECTION 1: Email
        "Email": client_email,
        
        # SECTION 2: Personal Details
        "Full Name": client_name,
        "DOB": "1990-01-01",
        "Gender": "Female" if random.random() > 0.5 else "Male",
        "WhatsApp Contact Number": f"+91{random.randint(7000000000, 9999999999)}",
        "Address": f"{random.randint(1, 999)} Wellness Avenue, Sector {random.randint(1, 50)}",
        "City": random.choice(["Surat", "Mumbai", "Delhi", "Bangalore", "Chennai"]),
        "PIN": f"{random.randint(100000, 999999)}",
        "State": random.choice(["Gujarat", "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu"]),
        "Country": "India",
        "Occupation": random.choice(["Software Engineer", "Doctor", "Teacher", "Business Owner", "Freelancer"]),
        "Marital Status": random.choice(["Married", "Single", "Other"]),
        
        # SECTION 3: Demographic and Lifestyle Information
        "Height (in cm)": str(random.randint(150, 190)),
        "Current Weight (in kg)": str(random.randint(50, 90)),
        "Target Weight (if any)": str(random.randint(50, 90)),
        "Primary Health Goals": ", ".join(random.sample([
            "Weight Loss", "Weight Gain", "Manage Chronic Disease", 
            "Improve Fitness & Stamina", "Boost Immunity", "Stress Management"
        ], k=random.randint(1, 3))),
        
        # SECTION 4: Medical History
        "Do you have any existing medical conditions?": random.choice(["Yes", "No"]),
        "If yes, please specify medical conditions.": "None" if random.random() > 0.5 else random.choice([
            "Occasional migraines", "Mild hypertension", "Type 2 diabetes", "Hypothyroidism"
        ]),
        "Are you currently on any medications?": random.choice(["Yes", "No"]),
        "If yes, please specify medications": "None" if random.random() > 0.5 else random.choice([
            "Blood pressure medication", "Thyroid medication", "Supplements only"
        ]),
        "Any allergies (food or otherwise)?": random.choice(["Yes", "No"]),
        "If yes, Please specify allergies.": "None" if random.random() > 0.7 else random.choice([
            "Dust", "Pollen", "Gluten sensitivity", "Lactose intolerance", "Nuts"
        ]),
        "Family Medical History: (e.g. diabetes, heart disease)": random.choice([
            "No significant history", "Diabetes in family", "Hypertension in parents", 
            "Father had heart disease", "Mother has hypothyroidism"
        ]),
        
        # SECTION 5: Daily Routine & Lifestyle
        "Wake-Up Time": f"{random.randint(5, 8)}:{random.choice(['00', '30'])} AM",
        "Sleep Time": f"{random.randint(9, 11)}:{random.choice(['00', '30'])} PM",
        "Average Hours of Sleep": str(random.randint(6, 9)),
        "Work Schedule": ", ".join(random.sample(["Fixed", "Rotational", "Remote", "Field Work"], k=random.randint(1, 2))),
        "Physical Activity Level": random.choice([
            "Sedentary (Minimal Activity)", 
            "Lightly Active (Light Exercise or Office Work)",
            "Moderately Active (Regular Exercise 3-4 times a week)",
            "Very Active (Intense Exercise or Physically Demanding Job)"
        ]),
        "Exercise Routine (if any)": random.choice([
            "30 minute walk daily", "Yoga twice a week", "Gym 3-4 times a week",
            "None currently", "Running 2-3 times a week"
        ]),
        "Stress Level": random.choice(["Low", "Moderate", "High"]),
        "Screen Time per Day (in Hours)": str(random.randint(2, 10)),
        
        # SECTION 6: Dietary Preferences and Habits
        "Dietary Preference": random.choice(["Vegetarian", "Non-Vegetarian", "Vegan", "Mixed Diet (Veg + Non Veg)", "Gluten-free", "Jain"]),
        "Any Dietary Restrictions?": random.choice(["Yes", "No"]),
        "If yes, Please specify Dietary Restrictions": "None" if random.random() > 0.6 else random.choice([
            "No onion and garlic", "Gluten-free", "Dairy-free", "No eggs", "Low sodium"
        ]),
        "Meals per Day": random.choice(["2", "3", "4", "More"]),
        "Snacking Habit": random.choice(["Yes", "No", "Occasionally"]),
        "Water Intake Per Day (in Liters)": f"{random.randint(15, 40) / 10:.1f}",
        "Consumption of Caffeine (Tea/Coffee) Cups Per Day": str(random.randint(0, 5)),
        "Frequency of Eating Out": random.choice(["Rarely", "Weekly", "Monthly", "Frequently"]),
        
        # SECTION 7: Mental and Emotional Well-being
        "How often do you feel stressed?": random.choice(["Rarely", "Sometimes", "Often"]),
        "Do you practice any relaxation techniques?": random.choice(["Yes", "No"]),
        "If yes, Specify relaxation techniques.": "None" if random.random() > 0.5 else random.choice([
            "Meditation", "Deep breathing exercises", "Yoga", "Mindfulness", "Walking in nature"
        ]),
        "Hobbies and Leisure Activities (Describe)": random.choice([
            "Reading, gardening", "Music, movies", "Cooking, traveling", 
            "Sports, video games", "Painting, crafts"
        ]),
        
        # SECTION 8: Additional Information
        "Any specif concerns or goals you would like to address?": random.choice([
            "Would like to manage stress better and establish a sustainable routine",
            "Need help with portion control and meal planning",
            "Looking to increase energy levels throughout the day",
            "Want to improve sleep quality and reduce screen time",
            "Test submission for monitoring"
        ]),
        "Have you followed any diet or fitness plan before?": random.choice(["Yes", "No"]),
        "If yes, what type and what were the results?": "None" if random.random() > 0.5 else random.choice([
            "Tried intermittent fasting for 3 months with mixed results",
            "Followed a keto diet but couldn't maintain it long-term",
            "Did gym training for 6 months and saw good results",
            "Tried various diets with limited success"
        ]),
        "Food Budget": random.choice(["Low", "Medium", "High"]),
        "Additional Information": "Test submission for monitoring. Please ignore this automated test."
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
    print(f"Sender Email: {os.environ.get('SENDER_EMAIL', 'desaiaditya2710@gmail.com')}")
    
    # Generate test data
    form_data = generate_test_data(args.client_name, args.client_email, args.use_simulator)
    
    # Submit the form
    submission_id = submit_form(args.api_endpoint, form_data)
    
    if submission_id:
        # Monitor the job in DynamoDB
        monitor_job_in_dynamodb(submission_id, args.region)
        
        # Inform the user about the email
        print(f"\nThe wellness plan will be emailed to: {form_data['Email']}")
        print(f"From sender address: {os.environ.get('SENDER_EMAIL', 'desaiaditya2710@gmail.com')}")
        print("Check your inbox (and spam folder) for the wellness plan email.")
        
        # If using a real email address, remind about verification
        if not form_data['Email'].endswith('@simulator.amazonses.com'):
            print("\nNOTE: If your AWS SES account is in sandbox mode, ensure both the sender")
            print("      and recipient email addresses are verified in SES.")
        else:
            print("\nNOTE: Using Amazon SES simulator for testing.")
    
    print("\n=== Monitoring Complete ===")

if __name__ == "__main__":
    # Suppress InsecureRequestWarning for testing
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main() 