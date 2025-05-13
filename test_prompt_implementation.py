#!/usr/bin/env python3
"""
Test for the prompt implementation.

This script tests the new implementation that feeds the prompt.txt file directly
to the Gemini API with the client data JSON file. It simulates the behavior
of the Lambda functions without requiring a full AWS deployment.
"""

import json
import os
import sys
import requests
import time
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Gemini API configuration
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_K = 40
DEFAULT_TOP_P = 0.95

def read_file(filename):
    """Read a file and return its contents."""
    with open(filename, 'r') as f:
        return f.read()

def call_gemini_api(prompt, client_data):
    """
    Call the Gemini API with the prompt template and client data.
    
    Args:
        prompt: The standard prompt template
        client_data: The client data dictionary
        
    Returns:
        Generated response from Gemini
    """
    # Get API key from environment variable
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set it using: export GEMINI_API_KEY=your-api-key")
        sys.exit(1)
    
    # API endpoint
    model_name = DEFAULT_GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
    
    # Format the client data as a clean JSON string
    client_data_str = json.dumps(client_data, indent=2)
    
    # Our complete message to Gemini includes both the prompt and the client data
    combined_message = f"{prompt}\n\n# CLIENT DATA (JSON):\n```json\n{client_data_str}\n```"
    
    # Request payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": combined_message
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": DEFAULT_TEMPERATURE,
            "topK": DEFAULT_TOP_K,
            "topP": DEFAULT_TOP_P,
            "maxOutputTokens": DEFAULT_MAX_OUTPUT_TOKENS
        }
    }
    
    print(f"Calling Gemini API with model: {model_name}")
    print("This may take a minute or two...")
    
    # Record start time
    start_time = time.time()
    
    # Make the API call
    response = requests.post(url, json=payload)
    
    # Record end time
    end_time = time.time()
    duration = end_time - start_time
    
    # Check for successful response
    if response.status_code != 200:
        print(f"Error: Gemini API returned status code {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    # Parse the response
    response_json = response.json()
    
    # Extract the text from the response
    try:
        text = response_json['candidates'][0]['content']['parts'][0]['text']
        return text, duration
    except (KeyError, IndexError) as e:
        print(f"Error extracting text from Gemini response: {str(e)}")
        print(f"Response: {json.dumps(response_json, indent=2)}")
        sys.exit(1)

def main():
    """Main function."""
    # Check if prompt.txt file exists in test-data directory
    prompt_file = "test-data/prompt.txt"
    if not os.path.exists(prompt_file):
        print(f"Error: Prompt file not found at {prompt_file}")
        sys.exit(1)
    
    # Check if sample client data file exists
    client_data_file = "test-data/sample-form-submission.json"
    if not os.path.exists(client_data_file):
        print(f"Error: Client data file not found at {client_data_file}")
        sys.exit(1)
    
    # Read the prompt and client data
    print(f"Reading prompt from {prompt_file}")
    prompt = read_file(prompt_file)
    
    print(f"Reading client data from {client_data_file}")
    client_data = json.loads(read_file(client_data_file))
    
    # Create output directories if they don't exist
    os.makedirs("test_output", exist_ok=True)
    os.makedirs("test_output/prompt_implementation", exist_ok=True)
    
    # Call Gemini API
    print("Calling Gemini API with prompt and client data...")
    response, duration = call_gemini_api(prompt, client_data)
    
    # Write response to file
    output_file = "test_output/prompt_implementation/gemini_response.md"
    with open(output_file, 'w') as f:
        f.write(response)
    
    print(f"Gemini API call completed in {duration:.2f} seconds")
    print(f"Response written to {output_file}")
    
    # Write a summary of what was tested
    with open("test_output/prompt_implementation/test_summary.txt", 'w') as f:
        f.write(f"Test prompt implementation\n")
        f.write(f"-------------------------\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Prompt file: {prompt_file}\n")
        f.write(f"Client data file: {client_data_file}\n")
        f.write(f"Model: {DEFAULT_GEMINI_MODEL}\n")
        f.write(f"Temperature: {DEFAULT_TEMPERATURE}\n")
        f.write(f"Response time: {duration:.2f} seconds\n")
        f.write(f"Output file: {output_file}\n")
    
    print("\nTest completed successfully!")
    print("You can now examine the Gemini response in the output file.")

if __name__ == "__main__":
    main() 