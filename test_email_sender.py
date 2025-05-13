#!/usr/bin/env python3
"""
Test script to directly test the send_email Lambda function.

This script simulates an event to the Lambda function, triggering
the email sending process with the SES simulator.
"""

import sys
import os
import json
import uuid
import argparse
import boto3
from datetime import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test the send_email Lambda function.')
    parser.add_argument('--sender', type=str, default='desaiaditya2710@gmail.com', 
                        help='Sender email address (must be verified in SES)')
    parser.add_argument('--simulator', type=str, default='success@simulator.amazonses.com',
                        choices=['success@simulator.amazonses.com',
                                'bounce@simulator.amazonses.com',
                                'complaint@simulator.amazonses.com'],
                        help='SES simulator address to use')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    return parser.parse_args()

def patch_aws_clients(region):
    """Patch boto3 to use the specified region."""
    # Save the original boto3 resource and client functions
    original_resource = boto3.resource
    original_client = boto3.client
    
    # Create patched versions that include the region
    def patched_resource(service_name, *args, **kwargs):
        if 'region_name' not in kwargs:
            kwargs['region_name'] = region
        return original_resource(service_name, *args, **kwargs)
    
    def patched_client(service_name, *args, **kwargs):
        if 'region_name' not in kwargs:
            kwargs['region_name'] = region
        return original_client(service_name, *args, **kwargs)
    
    # Apply the patches
    boto3.resource = patched_resource
    boto3.client = patched_client
    
    print(f"Patched boto3 to use region: {region}")

def upload_test_pdf(s3_client, bucket_name):
    """Upload a test PDF to S3."""
    print("Creating and uploading test PDF...")
    
    # Generate a sample PDF file
    try:
        # Check if we can import the required modules
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        # Create a simple PDF
        buffer = BytesIO()
        c = canvas.Canvas(buffer)
        c.drawString(100, 750, "Test Wellness Plan")
        c.drawString(100, 700, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, 650, "This is a test PDF for the HRIM system.")
        c.save()
        
        # Get the PDF data
        pdf_data = buffer.getvalue()
        
        # Generate key for the PDF
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_key = f"test-pdfs/test-wellness-plan-{timestamp}.pdf"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=pdf_key,
            Body=pdf_data,
            ContentType='application/pdf'
        )
        
        print(f"Test PDF uploaded to s3://{bucket_name}/{pdf_key}")
        return pdf_key, f"test-wellness-plan-{timestamp}.pdf"
    except ImportError:
        print("ReportLab not installed. Using a mock PDF key.")
        # Use a mock PDF key if ReportLab is not installed
        pdf_key = "test-pdfs/mock-wellness-plan.pdf"
        return pdf_key, "mock-wellness-plan.pdf"

def main():
    """Main function."""
    args = parse_arguments()
    
    # Set environment variables
    os.environ['SENDER_EMAIL'] = args.sender
    os.environ['JOB_TABLE_NAME'] = 'hrim-jobs'
    os.environ['INPUT_BUCKET'] = 'hrim-input-data'
    os.environ['OUTPUT_BUCKET'] = 'hrim-output-data'
    
    # Patch boto3 to use the specified region
    patch_aws_clients(args.region)
    
    print("=== Testing send_email Lambda Function ===")
    print(f"Sender: {args.sender}")
    print(f"Recipient: {args.simulator}")
    
    # Import lambda_function after patching boto3
    sys.path.append('src/lambda/send_email')
    import lambda_function
    
    # Create S3 client
    s3_client = boto3.client('s3')
    
    # Create a test PDF and upload to S3
    pdf_key, pdf_filename = upload_test_pdf(s3_client, os.environ['OUTPUT_BUCKET'])
    
    # Create a job ID
    job_id = f"test-{uuid.uuid4()}"
    
    # Create client data
    client_data = {
        "Full Name": "Test Client",
        "Email": args.simulator,
        # Add other client data fields as needed
    }
    
    # Create the Lambda event
    event = {
        "job_id": job_id,
        "pdf_key": pdf_key,
        "pdf_filename": pdf_filename,
        "client_data": client_data
    }
    
    print(f"Invoking Lambda function with job_id: {job_id}")
    print(f"PDF Key: {pdf_key}")
    print(f"PDF Filename: {pdf_filename}")
    
    # Invoke the Lambda function
    try:
        print("\nCalling send_email Lambda function...")
        response = lambda_function.lambda_handler(event, None)
        
        print(f"\nResponse Status Code: {response.get('statusCode')}")
        body = json.loads(response.get('body', '{}'))
        
        if response.get('statusCode') == 200:
            print("✅ Email sent successfully!")
            print(f"Message ID: {body.get('message_id')}")
            print(f"Recipient: {body.get('recipient')}")
        else:
            print(f"❌ Error: {body.get('error')}")
            print(f"Details: {body.get('details')}")
    except Exception as e:
        print(f"❌ Error invoking Lambda function: {str(e)}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main() 