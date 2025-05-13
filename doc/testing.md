# Testing HRIM

This document provides instructions on how to test the HRIM system.

## Prerequisites

Before testing, make sure you have:

1. Python 3.11 or later installed
2. Required dependencies installed: `pip install -r requirements.txt`
3. A Google Gemini API key
4. AWS credentials configured (for email delivery tests)
5. A verified email address in AWS SES (for email delivery tests)

## Local Testing Without AWS

The easiest way to test the system locally without AWS deployment is to use the `test_hrim.py` script:

```bash
python test_hrim.py
```

This will:
1. Load the sample client data from `test-data/sample-form-submission.json`
2. Run through the entire workflow locally
3. Generate and save the PDF to `test_output/pdfs/`
4. Save all intermediate artifacts (prompt, Gemini response, etc.) to `test_output/`

The script creates local directories to mimic the S3 structure, so you can inspect the output.

## Testing with Real Email Delivery

To test with real email delivery via AWS SES:

1. Make sure your AWS credentials are configured
2. Verify your email address in AWS SES
3. Run the test script with your email as an argument:
   ```bash
   python test_hrim.py your-verified-email@example.com
   ```

The script will send the generated PDF to the specified email address.

## Testing Individual Components

If you want to test individual components:

### Data Fetching

To test data fetching:

```python
from src.lambda.fetch_data import lambda_function
from src.lambda import utils
import json

# Create a mock event
event = {
    'job_id': 'test-job-123', 
    'client_data_key': 'test-data/sample-form-submission.json'
}

# Set environment variables
import os
os.environ['INPUT_BUCKET'] = 'hrim-input-data-local'
os.environ['OUTPUT_BUCKET'] = 'hrim-output-data-local'
os.environ['JOB_TABLE_NAME'] = 'hrim-jobs-local'

# Call the function
response = lambda_function.lambda_handler(event, None)
print(json.dumps(response, indent=2))
```

### Prompt Formatting

To test prompt formatting:

```python
from src.lambda.format_prompt import lambda_function
import json

# Load client data
with open('test-data/sample-form-submission.json', 'r') as f:
    client_data = json.load(f)

# Create a mock event
event = {
    'job_id': 'test-job-123',
    'client_data': client_data
}

# Call the function
response = lambda_function.lambda_handler(event, None)
print(response)
```

### Gemini API Testing

To test the Gemini API integration:

```python
from src.lambda.call_gemini import lambda_function
import os
import json

# Set your Gemini API key
os.environ['GEMINI_API_KEY'] = 'your-gemini-api-key'

# Load a test prompt
with open('test_output/prompt_test-job-123.txt', 'r') as f:
    prompt = f.read()

# Create a mock event
event = {
    'job_id': 'test-job-123',
    'prompt': prompt,
    'client_data': {'Full Name': 'Test Client'}
}

# Call the function
response = lambda_function.lambda_handler(event, None)
print(response)
```

### PDF Generation Testing

To test PDF generation:

```python
from src.lambda.generate_pdf import lambda_function
import json

# Load a test Gemini response
with open('test_output/gemini_response_test-job-123.md', 'r') as f:
    response_md = f.read()

# Load client data
with open('test-data/sample-form-submission.json', 'r') as f:
    client_data = json.load(f)

# Create a mock event
event = {
    'job_id': 'test-job-123',
    'response': response_md,
    'client_data': client_data
}

# Call the function
response = lambda_function.lambda_handler(event, None)
print(response)
```

### Email Delivery Testing

To test email delivery:

```python
from src.lambda.send_email import lambda_function
import json
import os

# Set your AWS credentials and region
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['SENDER_EMAIL'] = 'your-verified-email@example.com'

# Create a mock event with PDF key
event = {
    'job_id': 'test-job-123',
    'pdf_key': 'jobs/test-job-123/Kavita_Kapoor_wellness_plan_20250513_123456.pdf',
    'pdf_filename': 'Kavita_Kapoor_wellness_plan_20250513_123456.pdf',
    'client_data': {
        'Full Name': 'Kavita Kapoor',
        'Email': 'your-verified-email@example.com'
    }
}

# Call the function
response = lambda_function.lambda_handler(event, None)
print(response)
```

## Testing with Different Client Data

To test with different client data:

1. Create a new JSON file in the `test-data` directory
2. Follow the format of the sample submission
3. Run the test script with a file path argument:
   ```bash
   python test_hrim.py --data-file test-data/your-custom-data.json
   ```

## Troubleshooting

If you encounter issues:

1. **Gemini API Error**: Verify your API key is correct and that you have access to Gemini 1.5.
2. **Email Delivery Error**: Ensure your AWS credentials are configured and the email is verified in SES.
3. **PDF Generation Error**: Check the Gemini response format; it should be well-structured markdown.
4. **General Errors**: See the log output for detailed error messages.

For API-specific errors, check the Gemini API documentation at: https://ai.google.dev/docs 