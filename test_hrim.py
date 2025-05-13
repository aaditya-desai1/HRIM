#!/usr/bin/env python3
"""
Test script for the HRIM (Health & Wellness Report Implementation Manager) system.

This script simulates the entire workflow:
1. Loads sample client data
2. Calls each lambda function in sequence
3. Generates the wellness plan and sends it via email

Usage:
    python test_hrim.py [optional-email-address] [--data-file file_path]

If an email address is provided, the script will send the PDF to that address.
Otherwise, it will just save the PDF locally.

You can also specify a custom data file using the --data-file flag.
"""

import json
import os
import sys
import logging
import uuid
import importlib
import tempfile
import argparse
from datetime import datetime
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_hrim')

# Create output directory
os.makedirs('test_output', exist_ok=True)
os.makedirs('test_output/pdfs', exist_ok=True)

# Configure AWS for local development
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Set dummy AWS credentials for local testing
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'

# Set up mock DynamoDB environment
os.environ['JOB_TABLE_NAME'] = 'hrim-jobs-local'
os.environ['INPUT_BUCKET'] = 'hrim-input-data-local'
os.environ['OUTPUT_BUCKET'] = 'hrim-output-data-local'

# Set Gemini API key (you'll need to provide a real key for testing)
if 'GEMINI_API_KEY' not in os.environ:
    logger.warning("GEMINI_API_KEY not found in environment variables, providing default test key")
    os.environ['GEMINI_API_KEY'] = "AIzaSyAYS1tFe_PDyoAQBsRHdQIWuQIrwgr2Q1w"

# Mock AWS services for local testing
class MockDynamoDB:
    def __init__(self):
        self.tables = {}
        
    def Table(self, table_name):
        if table_name not in self.tables:
            self.tables[table_name] = MockDynamoTable(table_name)
        return self.tables[table_name]

class MockDynamoTable:
    def __init__(self, table_name):
        self.name = table_name
        self.items = {}
        
    def put_item(self, Item):
        key = Item.get('job_id')
        if key:
            self.items[key] = Item
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}
        
    def get_item(self, Key):
        key = Key.get('job_id')
        if key and key in self.items:
            return {"Item": self.items[key]}
        return {}
        
    def update_item(self, Key, UpdateExpression=None, ExpressionAttributeValues=None, ExpressionAttributeNames=None):
        key = Key.get('job_id')
        if key and key in self.items:
            # Simple mock update - in real code would parse expressions
            if ExpressionAttributeValues and ':status' in ExpressionAttributeValues:
                self.items[key]['status'] = ExpressionAttributeValues.get(':status')
            if ExpressionAttributeValues and ':error' in ExpressionAttributeValues:
                self.items[key]['error'] = ExpressionAttributeValues.get(':error')
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

class MockS3:
    def __init__(self):
        self.objects = {}
        
    def upload_fileobj(self, file_obj, bucket, key, ExtraArgs=None):
        if bucket not in self.objects:
            self.objects[bucket] = {}
        file_obj.seek(0)
        content = file_obj.read()
        self.objects[bucket][key] = content
        # Save to local test output for inspection
        os.makedirs(f"test_output/{bucket}/{os.path.dirname(key)}", exist_ok=True)
        with open(f"test_output/{bucket}/{key}", 'wb') as f:
            f.write(content)
        return True
        
    def download_fileobj(self, bucket, key, file_obj):
        """Mock implementation of download_fileobj"""
        if bucket in self.objects and key in self.objects[bucket]:
            content = self.objects[bucket][key]
            # If content is a string, encode it as bytes
            if isinstance(content, str):
                content = content.encode('utf-8')
            file_obj.write(content)
            file_obj.seek(0)
            return True
            
        # Try to load from local test output if it exists
        try:
            path = f"test_output/{bucket}/{key}"
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    content = f.read()
                    file_obj.write(content)
                    file_obj.seek(0)
                    return True
        except Exception as e:
            logger.error(f"Error loading mock S3 object: {str(e)}")
            
        raise Exception(f"Mock S3 object not found: {bucket}/{key}")
        
    def put_object(self, Body, Bucket, Key, ContentType=None):
        if Bucket not in self.objects:
            self.objects[Bucket] = {}
        self.objects[Bucket][Key] = Body
        # Save to local test output for inspection
        os.makedirs(f"test_output/{Bucket}/{os.path.dirname(Key)}", exist_ok=True)
        try:
            mode = 'wb' if isinstance(Body, bytes) else 'w'
            with open(f"test_output/{Bucket}/{Key}", mode) as f:
                f.write(Body)
        except Exception as e:
            logger.error(f"Error saving mock S3 object: {str(e)}")
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}
        
    def get_object(self, Bucket, Key):
        if Bucket in self.objects and Key in self.objects[Bucket]:
            return {"Body": MockS3Object(self.objects[Bucket][Key])}
        
        # Try to load from test_output if it exists
        try:
            path = f"test_output/{Bucket}/{Key}"
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    content = f.read()
                    return {"Body": MockS3Object(content)}
        except Exception as e:
            logger.error(f"Error loading mock S3 object: {str(e)}")
            
        raise Exception(f"Mock S3 object not found: {Bucket}/{Key}")
        
    def generate_presigned_url(self, ClientMethod, Params=None, ExpiresIn=3600, HttpMethod=None):
        """Mock implementation of generate_presigned_url"""
        if Params and 'Bucket' in Params and 'Key' in Params:
            bucket = Params['Bucket']
            key = Params['Key']
            # Create a mock URL that points to the local test output
            return f"file://{os.path.abspath(f'test_output/{bucket}/{key}')}"
        return "https://mock-presigned-url.example.com/mock-file"

class MockS3Object:
    def __init__(self, content):
        self.content = content
        
    def read(self):
        # If content is already bytes, return it directly
        if isinstance(self.content, bytes):
            return self.content
        # If content is a string, encode it as UTF-8
        elif isinstance(self.content, str):
            return self.content.encode('utf-8')
        # Otherwise, convert to string and then encode
        else:
            return str(self.content).encode('utf-8')

class MockSES:
    def __init__(self):
        self.emails = []
        
    def send_raw_email(self, RawMessage, Source=None, Destinations=None):
        self.emails.append({
            'source': Source,
            'destinations': Destinations,
            'message': RawMessage
        })
        message_id = f"mock-message-{len(self.emails)}"
        logger.info(f"Mock email sent. Message ID: {message_id}")
        return {"MessageId": message_id}

# Monkey patch boto3 with our mock services
import boto3

# Store the real boto3 resource and client functions
real_boto3_resource = boto3.resource
real_boto3_client = boto3.client

# Create mock instances
mock_dynamodb = MockDynamoDB()
mock_s3 = MockS3()
mock_ses = MockSES()

# Override boto3.resource
def mock_resource(service_name, *args, **kwargs):
    if service_name == 'dynamodb':
        return mock_dynamodb
    return real_boto3_resource(service_name, *args, **kwargs)

# Override boto3.client
def mock_client(service_name, *args, **kwargs):
    if service_name == 's3':
        return mock_s3
    elif service_name == 'ses':
        return mock_ses
    return real_boto3_client(service_name, *args, **kwargs)

# Apply the monkey patches
boto3.resource = mock_resource
boto3.client = mock_client


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test the HRIM workflow.')
    parser.add_argument('email', nargs='?', help='Email address to send the PDF to')
    parser.add_argument('--data-file', dest='data_file', help='Path to the client data file')
    parser.add_argument('--local', action='store_true', help='Run in local mode with all mocks')
    return parser.parse_args()


def load_test_data(file_path=None):
    """
    Load sample client data.
    
    Args:
        file_path: Optional path to a custom data file
        
    Returns:
        Client data as a dictionary
    """
    if file_path and os.path.exists(file_path):
        test_data_path = file_path
    else:
        test_data_path = os.path.join('test-data', 'sample-form-submission.json')
    
    if not os.path.exists(test_data_path):
        logger.error(f"Test data not found: {test_data_path}")
        return None
    
    with open(test_data_path, 'r') as f:
        return json.load(f)


def simulate_lambda_execution(module_name, event, context=None):
    """
    Simulate execution of a Lambda function.
    
    Args:
        module_name: The module name (e.g., 'trigger_processor')
        event: The event dict to pass to the Lambda function
        context: Optional Lambda context object
        
    Returns:
        The Lambda function's response
    """
    logger.info(f"Executing {module_name} lambda function")
    
    # Import the lambda function module dynamically
    module_path = f"src.lambda.{module_name}.lambda_function"
    lambda_module = importlib.import_module(module_path)
    
    # Call the lambda_handler function
    response = lambda_module.lambda_handler(event, context)
    
    # If the response has a 'body' field, parse it from JSON
    if isinstance(response, dict) and 'body' in response:
        if isinstance(response['body'], str):
            response['body'] = json.loads(response['body'])
    
    return response


def run_test(email=None, data_file=None, local=True):
    """
    Run the HRIM test workflow.
    
    Args:
        email: Optional email address to send the PDF to
        data_file: Optional path to a custom data file
        local: Whether to run in local mode with mocks
        
    Returns:
        Boolean indicating success or failure
    """
    start_time = datetime.now()
    logger.info("Starting HRIM test workflow")
    
    # Load test data
    client_data = load_test_data(data_file)
    if not client_data:
        logger.error("Failed to load test data")
        return False
    
    # Save test data to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
        json.dump(client_data, tmp)
        tmp_path = tmp.name
    
    # Create a mock S3 event
    s3_key = f"incoming/{os.path.basename(tmp_path)}"
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
    
    # Simulate DynamoDB and S3 for local testing
    try:
        # Mock file in S3 by creating local version
        os.makedirs(f"test_output/{os.environ['INPUT_BUCKET']}/{os.path.dirname(s3_key)}", exist_ok=True)
        with open(f"test_output/{os.environ['INPUT_BUCKET']}/{s3_key}", 'w') as f:
            f.write(json.dumps(client_data))
        
        # Call the trigger_processor lambda
        trigger_response = simulate_lambda_execution('trigger_processor', s3_event)
        logger.info(f"Trigger processor response: {json.dumps(trigger_response, indent=2)}")
        
        if trigger_response['statusCode'] != 200:
            logger.error(f"Trigger processor failed: {trigger_response['body']['error']}")
            return False
        
        # Extract job ID and prepare fetch_data event
        job_id = trigger_response['body']['jobs'][0]['job_id']
        logger.info(f"Job ID: {job_id}")
        
        # Prepare fetch_data event
        fetch_event = {
            'job_id': job_id,
            'client_data_key': s3_key
        }
        
        # Call the fetch_data lambda
        fetch_response = simulate_lambda_execution('fetch_data', fetch_event)
        logger.info(f"Fetch data response: {json.dumps(fetch_response, indent=2)}")
        
        if fetch_response['statusCode'] != 200:
            logger.error(f"Fetch data failed: {fetch_response['body']['error']}")
            return False
        
        # Prepare format_prompt event
        format_event = {
            'job_id': job_id,
            'client_data': client_data
        }
        
        # Call the format_prompt lambda
        format_response = simulate_lambda_execution('format_prompt', format_event)
        logger.info(f"Format prompt response: {json.dumps(format_response, indent=2)}")
        
        if format_response['statusCode'] != 200:
            logger.error(f"Format prompt failed: {format_response['body']['error']}")
            return False
        
        # Extract prompt and prepare call_gemini event
        prompt = format_response['body']['prompt']
        
        # Save the prompt for inspection
        with open(f"test_output/prompt_{job_id}.txt", 'w') as f:
            f.write(prompt)
        logger.info(f"Prompt saved to test_output/prompt_{job_id}.txt")
        
        # Prepare call_gemini event
        gemini_event = {
            'job_id': job_id,
            'prompt': prompt,
            'client_data': client_data
        }
        
        # Call the call_gemini lambda
        gemini_response = simulate_lambda_execution('call_gemini', gemini_event)
        logger.info(f"Call Gemini response status: {gemini_response['statusCode']}")
        
        if gemini_response['statusCode'] != 200:
            logger.error(f"Call Gemini failed: {gemini_response['body']['error']}")
            return False
        
        # Extract Gemini response and prepare generate_pdf event
        ai_response = gemini_response['body']['response']
        
        # Save the AI response for inspection
        with open(f"test_output/gemini_response_{job_id}.md", 'w') as f:
            f.write(ai_response)
        logger.info(f"Gemini response saved to test_output/gemini_response_{job_id}.md")
        
        # Prepare generate_pdf event
        pdf_event = {
            'job_id': job_id,
            'response': ai_response,
            'client_data': client_data
        }
        
        # Call the generate_pdf lambda
        pdf_response = simulate_lambda_execution('generate_pdf', pdf_event)
        logger.info(f"Generate PDF response: {json.dumps(pdf_response, indent=2)}")
        
        if pdf_response['statusCode'] != 200:
            logger.error(f"Generate PDF failed: {pdf_response['body']['error']}")
            return False
        
        # Extract PDF key and prepare upload_pdf event
        pdf_key = pdf_response['body']['pdf_key']
        pdf_filename = pdf_response['body']['pdf_filename']
        
        # Prepare upload_pdf event
        upload_event = {
            'job_id': job_id,
            'pdf_key': pdf_key,
            'pdf_filename': pdf_filename,
            'client_data': client_data
        }
        
        # Call the upload_pdf lambda
        upload_response = simulate_lambda_execution('upload_pdf', upload_event)
        logger.info(f"Upload PDF response: {json.dumps(upload_response, indent=2)}")
        
        if upload_response['statusCode'] != 200:
            logger.error(f"Upload PDF failed: {upload_response['body']['error']}")
            return False
        
        # If an email address was provided, send the email
        if email:
            # Override client email with provided email
            client_data['Email'] = email
            
            # Prepare send_email event
            email_event = {
                'job_id': job_id,
                'pdf_key': pdf_key,
                'pdf_filename': pdf_filename,
                'client_data': client_data
            }
            
            # If we're using a real email address, set the sender email
            if not local and os.environ.get('SENDER_EMAIL'):
                os.environ['SENDER_EMAIL'] = email
            
            # Call the send_email lambda
            email_response = simulate_lambda_execution('send_email', email_event)
            logger.info(f"Send Email response: {json.dumps(email_response, indent=2)}")
            
            # Print mock email details for inspection
            if mock_ses.emails:
                logger.info("Mock Email Details:")
                for i, email in enumerate(mock_ses.emails):
                    logger.info(f"Email {i+1}:")
                    if 'source' in email:
                        logger.info(f"  From: {email['source']}")
                    if 'destinations' in email and email['destinations']:
                        logger.info(f"  To: {', '.join(email['destinations'])}")
                    if 'message' in email and 'Data' in email['message']:
                        # Print a shortened version of the message
                        msg_data = email['message']['Data']
                        if isinstance(msg_data, bytes):
                            # Convert binary data to string for preview
                            try:
                                msg_str = msg_data.decode('utf-8')
                            except UnicodeDecodeError:
                                msg_str = "(Binary data)"
                        else:
                            msg_str = str(msg_data)
                            
                        msg_preview = msg_str[:500] + "..." if len(msg_str) > 500 else msg_str
                        logger.info(f"  Message Preview: {msg_preview}")
            
            if email_response['statusCode'] != 200:
                logger.error(f"Send Email failed: {email_response['body']['error']}")
                return False
            
            if local:
                logger.info("Email would be sent to: " + email)
        else:
            logger.info("Skipping email sending (no email address provided)")
        
        # Prepare complete_job event
        complete_event = {
            'job_id': job_id
        }
        
        # Call the complete_job lambda
        complete_response = simulate_lambda_execution('complete_job', complete_event)
        logger.info(f"Complete Job response: {json.dumps(complete_response, indent=2)}")
        
        if complete_response['statusCode'] != 200:
            logger.error(f"Complete Job failed: {complete_response['body']['error']}")
            return False
        
        # Calculate total processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Workflow completed successfully in {processing_time:.2f} seconds")
        logger.info(f"PDF output available at: test_output/pdfs/{pdf_filename}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error during test workflow: {str(e)}", exc_info=True)
        return False
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    args = parse_arguments()
    
    if args.email:
        logger.info(f"Email provided as argument: {args.email}")
    
    if args.data_file:
        logger.info(f"Using custom data file: {args.data_file}")
    
    success = run_test(email=args.email, data_file=args.data_file, local=args.local)
    sys.exit(0 if success else 1) 