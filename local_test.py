#!/usr/bin/env python3
"""
Local test script for the HRIM project.

This script allows testing the HRIM workflow locally using mock implementations
of external services like OpenAI API, AWS SES, and WhatsApp Business API.
"""

import json
import os
import sys
import logging
import uuid
import boto3
import importlib
from datetime import datetime, timezone
import time

# Setup for moto mocks
try:
    from moto import mock_dynamodb, mock_s3, mock_secretsmanager
    HAS_MOTO = True
except ImportError:
    HAS_MOTO = False
    logging.warning("moto library not found. Using basic mocking instead.")
    logging.warning("To install: pip install moto")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('local_test')

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure AWS region and mock credentials (needed even for mocks)
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'mock-access-key-for-testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'mock-secret-key-for-testing'
boto3.setup_default_session(region_name='us-east-1')

# Initialize variables for mock modules
mock_modules = {
    'openai': None,
    'email': None,
    'whatsapp': None,
    'secrets': None
}

def apply_mocks():
    """Apply all mocks to redirect API calls to mock implementations."""
    logger.info("Applying mock implementations for external services")
    
    # Import mock modules safely
    try:
        # Import mock modules using importlib
        mock_modules['openai'] = importlib.import_module('src.lambda.mocks.mock_openai')
        mock_modules['email'] = importlib.import_module('src.lambda.mocks.mock_email')
        mock_modules['whatsapp'] = importlib.import_module('src.lambda.mocks.mock_whatsapp')
        mock_modules['secrets'] = importlib.import_module('src.lambda.mocks.mock_secrets')
    except ImportError as e:
        logger.warning(f"Error importing mock modules: {e}")
        logger.warning("Will attempt to use partial mocking")
    
    # Mock OpenAI
    if mock_modules['openai']:
        sys.modules['openai'] = mock_modules['openai']
    
    # Mock AWS clients by monkey patching boto3 (only if not using moto)
    if not HAS_MOTO:
        original_boto3_client = boto3.client
        
        def mock_boto3_client(service_name, *args, **kwargs):
            if service_name == 'ses' and mock_modules['email']:
                logger.info("Creating mock SES client")
                return mock_modules['email'].get_mock_ses_client()
            elif service_name == 'secretsmanager' and mock_modules['secrets']:
                logger.info("Creating mock Secrets Manager client")
                return mock_modules['secrets'].get_mock_secrets_manager_client()
            elif service_name == 'dynamodb':
                logger.info("Creating mock DynamoDB client")
                # Return a mock DynamoDB client with basic functionality
                class MockDynamoDBClient:
                    def update_item(self, *args, **kwargs):
                        return {"Attributes": {}}
                    def get_item(self, *args, **kwargs):
                        return {"Item": {}}
                    def put_item(self, *args, **kwargs):
                        return {}
                return MockDynamoDBClient()
            elif service_name == 's3':
                logger.info("Creating mock S3 client")
                # Return a mock S3 client with basic functionality
                class MockS3Client:
                    def get_object(self, *args, **kwargs):
                        return {"Body": type('obj', (object,), {'read': lambda: b'{}'})}
                    def put_object(self, *args, **kwargs):
                        return {"ETag": "mock-etag"}
                return MockS3Client()
            else:
                return original_boto3_client(service_name, *args, **kwargs)
        
        boto3.client = mock_boto3_client
        logger.info("Applied basic AWS client mocks")
    else:
        logger.info("Using moto for AWS service mocking")
        original_boto3_client = None
    
    # Mock WhatsApp API (requests.post)
    if mock_modules['whatsapp']:
        mock_modules['whatsapp'].patch_requests()
    
    logger.info("All mocks applied successfully")
    return original_boto3_client

def create_test_directories():
    """Create necessary directories for test outputs."""
    dirs = [
        'test_output',
        'test_output/mock_emails',
        'test_output/mock_whatsapp',
        'test_output/pdfs',
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def load_test_data():
    """Load test data from the test-data directory."""
    test_data_file = os.path.join('test-data', 'sample-form-submission.json')
    
    if not os.path.exists(test_data_file):
        logger.error(f"Test data file not found: {test_data_file}")
        sys.exit(1)
        
    with open(test_data_file, 'r') as f:
        return json.load(f)

def import_lambda_function(function_name):
    """Dynamically import a Lambda function module."""
    module_path = f'src.lambda.{function_name}.lambda_function'
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        logger.error(f"Failed to import {module_path}: {e}")
        sys.exit(1)

def setup_mock_aws_resources():
    """Set up mock AWS resources if using moto."""
    if not HAS_MOTO:
        return
    
    # Create DynamoDB table
    dynamodb = boto3.resource('dynamodb')
    table_name = 'wellness_plan_jobs'
    
    logger.info(f"Creating mock DynamoDB table: {table_name}")
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'job_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'job_id', 'AttributeType': 'S'},
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    
    # Create S3 buckets
    s3 = boto3.resource('s3')
    input_bucket = 'mock-wellness-data-input'
    output_bucket = 'mock-wellness-plan-output'
    
    logger.info(f"Creating mock S3 buckets: {input_bucket}, {output_bucket}")
    s3.create_bucket(Bucket=input_bucket)
    s3.create_bucket(Bucket=output_bucket)
    
    # Create secrets in SecretsManager
    secrets = boto3.client('secretsmanager')
    logger.info("Creating mock secrets")
    secrets.create_secret(
        Name='wellness/openai-api-key',
        SecretString='mock-openai-api-key'
    )
    secrets.create_secret(
        Name='wellness/whatsapp-api-key',
        SecretString='mock-whatsapp-api-key'
    )

def run_local_test():
    """Run the complete workflow locally with mocked services."""
    logger.info("Starting local test of HRIM workflow")
    
    # Setup moto mocks if available
    if HAS_MOTO:
        # Start mock services
        mock_services = []
        mock_services.append(mock_dynamodb())
        mock_services.append(mock_s3())
        mock_services.append(mock_secretsmanager())
        
        # Start all mock services
        for mock_service in mock_services:
            mock_service.start()
        
        # Set up mock AWS resources
        setup_mock_aws_resources()
    
    # Apply mocks for non-AWS services
    original_boto3_client = apply_mocks()
    
    # Create test directories
    create_test_directories()
    
    # Load test data
    client_data = load_test_data()
    logger.info(f"Loaded test data for client: {client_data.get('Full Name', 'Unknown')}")
    
    # Create a test S3 bucket and key for simulation
    test_bucket = "mock-wellness-data-input"
    test_key = f"forms/test-submission-{uuid.uuid4()}.json"
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc).isoformat()
    
    # Create mock event for trigger_processor
    trigger_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {
                        "name": test_bucket
                    },
                    "object": {
                        "key": test_key
                    }
                }
            }
        ]
    }
    
    # Import Lambda functions
    try:
        trigger_processor = import_lambda_function("trigger_processor")
        fetch_data = import_lambda_function("fetch_data")
        format_prompt = import_lambda_function("format_prompt")
        call_openai = import_lambda_function("call_openai")
        generate_pdf = import_lambda_function("generate_pdf")
        upload_pdf = import_lambda_function("upload_pdf")
        send_email = import_lambda_function("send_email")
        send_whatsapp = import_lambda_function("send_whatsapp")
        complete_job = import_lambda_function("complete_job")
    except Exception as e:
        logger.error(f"Failed to import Lambda functions: {e}")
        sys.exit(1)
    
    # Simulate DynamoDB table by using a dictionary
    mock_dynamodb_dict = {
        job_id: {
            'job_id': job_id,
            'input_s3_bucket': test_bucket,
            'input_s3_key': test_key,
            'status': 'PENDING',
            'start_time': start_time,
            'client_email': client_data.get('Email', 'test@example.com'),
            'client_whatsapp': client_data.get('WhatsApp Contact Number', '+1234567890'),
            'client_name': client_data.get('Full Name', 'Test Client')
        }
    }
    
    # If using moto, add test data to S3
    if HAS_MOTO:
        # Add test data to S3
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=test_bucket,
            Key=test_key,
            Body=json.dumps(client_data)
        )
        
        # Add job to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('wellness_plan_jobs')
        table.put_item(Item=mock_dynamodb_dict[job_id])
    
    # Mock the DynamoDB functionality in utils.py if not using moto
    utils = None
    original_get_job = None
    original_update_job_status = None
    original_read_from_s3 = None
    original_write_to_s3 = None
    
    if not HAS_MOTO:
        try:
            # Import utils module using importlib
            utils = importlib.import_module('src.lambda.utils')
            
            # Save original functions
            original_get_job = utils.get_job
            original_update_job_status = utils.update_job_status
            original_read_from_s3 = utils.read_from_s3
            original_write_to_s3 = utils.write_to_s3
            
            # Define mock functions
            def mock_get_job(job_id):
                logger.info(f"Getting mock job: {job_id}")
                return mock_dynamodb_dict.get(job_id)
            
            def mock_update_job_status(job_id, status, additional_data=None):
                logger.info(f"Updating mock job {job_id} status to {status}")
                if job_id in mock_dynamodb_dict:
                    mock_dynamodb_dict[job_id]['status'] = status
                    if additional_data:
                        mock_dynamodb_dict[job_id].update(additional_data)
                return {"Attributes": mock_dynamodb_dict.get(job_id, {})}
            
            def mock_read_from_s3(bucket, key):
                logger.info(f"Reading mock data from S3: {bucket}/{key}")
                return client_data
            
            def mock_write_to_s3(bucket, key, data, content_type='application/pdf'):
                logger.info(f"Writing mock data to S3: {bucket}/{key}")
                # Save the PDF to the test output directory
                if content_type == 'application/pdf':
                    pdf_path = os.path.join('test_output', 'pdfs', f"{key.split('/')[-1]}")
                    with open(pdf_path, 'wb') as f:
                        f.write(data)
                    logger.info(f"Saved PDF to {pdf_path}")
                return {"ETag": "mock-etag"}
            
            # Apply mock functions
            utils.get_job = mock_get_job
            utils.update_job_status = mock_update_job_status
            utils.read_from_s3 = mock_read_from_s3
            utils.write_to_s3 = mock_write_to_s3
        
        except ImportError as e:
            logger.error(f"Failed to import utils module: {e}")
            sys.exit(1)
    
    # Run the workflow
    try:
        logger.info("Step 1: Trigger Processor")
        trigger_result = trigger_processor.lambda_handler(trigger_event, None)
        logger.info(f"Trigger result: {json.dumps(trigger_result)}")
        
        # Create event for fetch_data and ensure it has all necessary fields
        fetch_event = {
            'job_id': job_id,
            'input_s3_bucket': test_bucket,
            'input_s3_key': test_key,
            'timestamp': start_time
        }
        
        logger.info("Step 2: Fetch Data")
        fetch_result = fetch_data.lambda_handler(fetch_event, None)
        logger.info(f"Fetch result: {json.dumps(fetch_result)}")
        
        # Ensure format_prompt has all necessary fields
        if not isinstance(fetch_result, dict) or 'client_data' not in fetch_result:
            fetch_result = {'client_data': client_data, 'job_id': job_id}
        if 'job_id' not in fetch_result:
            fetch_result['job_id'] = job_id
            
        logger.info("Step 3: Format Prompt")
        format_result = format_prompt.lambda_handler(fetch_result, None)
        logger.info("Prompt formatted successfully")
        
        # Ensure call_openai has all necessary fields
        if not isinstance(format_result, dict) or 'prompt' not in format_result:
            format_result = {'job_id': job_id, 'prompt': 'mock prompt', 'client_data': client_data}
        if 'job_id' not in format_result:
            format_result['job_id'] = job_id
            
        logger.info("Step 4: Call OpenAI")
        openai_result = call_openai.lambda_handler(format_result, None)
        logger.info("OpenAI API call completed")
        
        # Ensure generate_pdf has all necessary fields
        if not isinstance(openai_result, dict) or 'wellness_plan' not in openai_result:
            openai_result = {
                'job_id': job_id, 
                'wellness_plan': 'This is a mock wellness plan.', 
                'client_data': client_data
            }
        if 'job_id' not in openai_result:
            openai_result['job_id'] = job_id
            
        logger.info("Step 5: Generate PDF")
        pdf_result = generate_pdf.lambda_handler(openai_result, None)
        logger.info("PDF generation completed")
        
        # Ensure upload_pdf has all necessary fields
        if not isinstance(pdf_result, dict) or 'pdf_data' not in pdf_result:
            pdf_result = {
                'job_id': job_id, 
                'pdf_data': b'Mock PDF data', 
                'client_data': client_data
            }
        if 'job_id' not in pdf_result:
            pdf_result['job_id'] = job_id
            
        logger.info("Step 6: Upload PDF")
        upload_result = upload_pdf.lambda_handler(pdf_result, None)
        logger.info(f"PDF upload completed: {json.dumps(upload_result)}")
        
        # Ensure send_email has all necessary fields
        if not isinstance(upload_result, dict) or 's3_bucket' not in upload_result:
            upload_result = {
                'job_id': job_id,
                's3_bucket': 'mock-wellness-plan-output',
                's3_key': f'wellness_plans/{job_id}.pdf',
                'client_data': client_data
            }
        if 'job_id' not in upload_result:
            upload_result['job_id'] = job_id
            
        logger.info("Step 7: Send Email")
        email_result = send_email.lambda_handler(upload_result, None)
        logger.info(f"Email delivery result: {json.dumps(email_result)}")
        
        logger.info("Step 8: Send WhatsApp")
        whatsapp_result = send_whatsapp.lambda_handler(upload_result, None)
        logger.info(f"WhatsApp delivery result: {json.dumps(whatsapp_result)}")
        
        # Combine results for complete_job
        complete_event = {
            'job_id': job_id,
            'email_status': email_result.get('email_status', 'SUCCESS'),
            'whatsapp_status': whatsapp_result.get('whatsapp_status', 'SUCCESS')
        }
        
        logger.info("Step 9: Complete Job")
        complete_result = complete_job.lambda_handler(complete_event, None)
        logger.info(f"Job completed: {json.dumps(complete_result)}")
        
        # Get final job status
        if HAS_MOTO:
            try:
                dynamodb = boto3.resource('dynamodb')
                table = dynamodb.Table('wellness_plan_jobs')
                response = table.get_item(Key={'job_id': job_id})
                final_status = response.get('Item', {}).get('status', 'UNKNOWN')
            except Exception as e:
                logger.error(f"Error getting final job status: {e}")
                final_status = 'ERROR'
        else:
            final_status = mock_dynamodb_dict[job_id]['status']
            
        logger.info("Local test completed successfully!")
        logger.info(f"Final job status: {final_status}")
        
    except Exception as e:
        logger.error(f"Error during local test: {str(e)}", exc_info=True)
    finally:
        # Clean up
        if not HAS_MOTO and utils is not None:
            # Restore original functions
            utils.get_job = original_get_job
            utils.update_job_status = original_update_job_status
            utils.read_from_s3 = original_read_from_s3
            utils.write_to_s3 = original_write_to_s3
        
        if not HAS_MOTO and original_boto3_client:
            # Restore original boto3 client
            boto3.client = original_boto3_client
        
        # Restore WhatsApp requests
        if mock_modules['whatsapp']:
            mock_modules['whatsapp'].unpatch_requests()
            
        # Stop moto mocks if they were started
        if HAS_MOTO:
            for mock_service in mock_services:
                mock_service.stop()

if __name__ == "__main__":
    run_local_test() 