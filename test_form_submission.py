#!/usr/bin/env python3
"""
Test script for the Google Form to S3 integration.

This script simulates a form submission to the API Gateway endpoint.
It can be used to test the integration without needing to submit an actual Google Form.

Usage:
    python test_form_submission.py [API_ENDPOINT]

If API_ENDPOINT is not provided, the script will use a mock endpoint that just prints the data.
"""

import sys
import json
import requests
import argparse
from datetime import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test Google Form submission to HRIM.')
    parser.add_argument('api_endpoint', nargs='?', 
                      default='https://24hhe95i09.execute-api.us-east-1.amazonaws.com/dev/form-submission',
                      help='API Gateway endpoint URL')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode without sending actual requests')
    parser.add_argument('--client-name', type=str, default='Test User', help='Name of the test client')
    parser.add_argument('--client-email', type=str, default='success@simulator.amazonses.com', help='Email of the test client')
    parser.add_argument('--use-simulator', action='store_true', help='Use SES mailbox simulator instead of the provided email')
    return parser.parse_args()

def generate_test_form_data(client_name, client_email, use_simulator=False):
    """
    Generate test form data matching the Google Form structure.
    
    Args:
        client_name: Name to use for the test client
        client_email: Email to use for the test client
        use_simulator: If True, use the SES simulator email
        
    Returns:
        Dict containing form data
    """
    # If use_simulator is True, override the client_email
    if use_simulator:
        client_email = "success@simulator.amazonses.com"
        print(f"Using SES simulator email address: {client_email}")
        
    return {
        "Full Name": client_name,
        "Email": client_email,
        "DOB": "1990-01-01",
        "Gender": "Female",
        "Height": "165 cm",
        "Weight": "60 kg",
        "Occupation": "Software Engineer",
        "Medical Conditions": "None",
        "Allergies or Sensitivities": "None",
        "Current Medications": "None",
        "Dietary Preference": "Vegan",
        "Meals per Day": "3",
        "Usual Meal Times (Breakfast)": "8:00 AM",
        "Usual Meal Times (Lunch)": "1:00 PM",
        "Usual Meal Times (Dinner)": "7:00 PM",
        "Cuisine Preference": "Indian",
        "Food You Enjoy": "Lentils, rice, vegetables, fruits, nuts, spices",
        "Foods you Dislike": "Bitter gourd, eggplant",
        "Activity Level": "Moderate",
        "Current Exercise Routine": "30 minute walk daily",
        "Sleep Pattern": "11pm to 7am, occasionally disrupted",
        "Stress Level": "Moderate",
        "Daily Water Intake": "2 liters",
        "Wellness Goals": "Increase energy levels, improve digestion, maintain weight",
        "Weight Management Goal": "Maintain current weight",
        "Energy Level Concerns": "Low energy in afternoons",
        "Food Budget": "Medium",
        "Available Cooking Time": "30-45 minutes per meal",
        "Household Size": "2",
        "Previous Diet Plans": "None",
        "Additional Information": "I work long hours and need simple, quick recipes that can be prepared in advance."
    }

def send_to_api(api_endpoint, form_data):
    """
    Send form data to the API Gateway endpoint.
    
    Args:
        api_endpoint: The API Gateway endpoint URL
        form_data: Dict containing form data
        
    Returns:
        Response from the API
    """
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        
        print(f"Making request to: {api_endpoint}")
        print(f"Request headers: {headers}")
        print(f"Request payload: {json.dumps(form_data, indent=2)[:300]}... (truncated)")
        
        # Add timeout and disable SSL verification for testing
        response = requests.post(
            api_endpoint,
            json=form_data,
            headers=headers,
            timeout=30,  # 30 second timeout
            verify=False  # Disable SSL verification for testing
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        return response
    except requests.exceptions.Timeout:
        print("Request timed out. The API endpoint may be unresponsive.")
        return None
    except requests.exceptions.SSLError as e:
        print(f"SSL Error: {str(e)}")
        print("Try running with --mock flag if testing locally.")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {str(e)}")
        print("Check if the API endpoint is correct and accessible.")
        return None
    except Exception as e:
        print(f"Error sending data to API: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {repr(e)}")
        return None

def mock_send_to_api(form_data):
    """
    Mock sending form data to API (just prints the data).
    
    Args:
        form_data: Dict containing form data
        
    Returns:
        Mock response
    """
    print("\n=== Form Data that would be sent to API ===")
    print(json.dumps(form_data, indent=2))
    print("==========================================\n")
    
    # Create a mock response
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.text = json.dumps({
                'message': 'Form data received and processing started',
                'submissionId': f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            })
            
        def json(self):
            return json.loads(self.text)
    
    return MockResponse()

def main():
    """Main function."""
    args = parse_arguments()
    
    # Generate test form data
    form_data = generate_test_form_data(args.client_name, args.client_email, args.use_simulator)
    
    # Send data to API or mock it
    if args.mock or not args.api_endpoint:
        if not args.mock:
            print("\nNo API endpoint provided. Running in mock mode.")
        response = mock_send_to_api(form_data)
    else:
        print(f"\nSending form data to API: {args.api_endpoint}")
        print(f"Using email: {form_data['Email']} (Using simulator: {args.use_simulator})")
        response = send_to_api(args.api_endpoint, form_data)
    
    # Print response
    if response:
        print(f"Response status code: {response.status_code}")
        try:
            response_json = response.json()
            print("Response data:")
            print(json.dumps(response_json, indent=2))
        except:
            print("Response text:")
            print(response.text)
    else:
        print("No response received.")

if __name__ == "__main__":
    main() 