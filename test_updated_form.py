#!/usr/bin/env python3
"""
Test script for the updated form submission.

This script tests the updated form submission process by loading the sample form data
and passing it to the form_submission Lambda function locally.
"""

import json
import os
import sys
import uuid
from datetime import datetime

# Add the src directory to the path so we can import Lambda functions
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src/lambda/form_submission'))
import lambda_function

def main():
    """Main function to test the form submission process."""
    print("Testing updated form submission...")
    
    # Load the sample form submission data
    with open('test-data/sample-form-submission.json', 'r') as f:
        form_data = json.load(f)
    
    print(f"Loaded sample form data: {json.dumps(form_data, indent=2)}")
    
    # Create a mock event
    event = {
        'body': json.dumps(form_data)
    }
    
    # Test standardization directly
    print("\nTesting field standardization...")
    standardized = lambda_function.standardize_form_data(form_data)
    
    # Check specific field mappings
    mapping_checks = [
        ('Primary Health Goals', 'Wellness Goals'),
        ('DOB', 'Date of Birth'),
        ('WhatsApp Contact Number', 'Phone Number'),
        ('City', 'City'),
        ('Current Weight (in kg)', 'Weight'),
        ('Height (in cm)', 'Height'),
        ('Dietary Preference', 'Dietary Preference')
    ]
    
    print("\nChecking field mappings:")
    all_mappings_correct = True
    for source, target in mapping_checks:
        if source in form_data:
            if target in standardized and standardized[target] == form_data[source]:
                print(f"✅ {source} -> {target}: OK")
            else:
                print(f"❌ {source} -> {target}: FAILED")
                if target not in standardized:
                    print(f"   Field '{target}' not found in standardized data")
                else:
                    print(f"   Expected: {form_data[source]}")
                    print(f"   Got: {standardized[target]}")
                all_mappings_correct = False
        else:
            print(f"⚠️ {source} not found in input data")
    
    if all_mappings_correct:
        print("\n✅ All field mappings are correct!")
    else:
        print("\n❌ Some field mappings failed. Check the logs above.")
    
    # Call the Lambda function
    print("\nCalling form_submission Lambda function...")
    response = lambda_function.lambda_handler(event, None)
    
    print(f"\nResponse from Lambda function: {json.dumps(response, indent=2)}")
    
    # Parse the standardized data
    if response['statusCode'] == 200:
        body = json.loads(response['body'])
        submission_id = body.get('submissionId')
        
        print(f"\nForm submission successful!")
        print(f"Submission ID: {submission_id}")
        
        # Check if the file was created in the input bucket
        input_bucket = os.environ.get('INPUT_BUCKET', 'hrim-input-data')
        s3_key = f"incoming/{submission_id}"
        
        print(f"\nThe form data should be stored in S3 at:")
        print(f"s3://{input_bucket}/{s3_key}")
        
        print(f"\nTo view the standardized data, run:")
        print(f"aws s3 cp s3://{input_bucket}/{s3_key} - | jq")
    else:
        print(f"\nForm submission failed with status code: {response['statusCode']}")
        if 'body' in response:
            try:
                error_details = json.loads(response['body'])
                print(f"Error details: {json.dumps(error_details, indent=2)}")
            except:
                print(f"Error body: {response['body']}")

if __name__ == "__main__":
    main() 