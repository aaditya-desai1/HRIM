```markdown
# Backend Implementation Guide: Automated Wellness Plan Generation (GPT-4o)

**Version:** 1.0
**Date:** May 13, 2025

## 1. Document Header

This document outlines the backend design and implementation plan for a system that processes client wellness data from AWS S3, generates a personalized diet and wellness plan using the GPT-4o API, saves the plan as a PDF to S3, and sends it to the client via WhatsApp and Email.

## 2. API Design

This system is primarily **event-driven**, triggered by new data files arriving in an S3 bucket. While there isn't a typical request/response REST API for client interaction, the initiation point acts as the "API" for upstream systems.

### 2.1 Primary Trigger (Event-Driven)

*   **Mechanism:** AWS S3 Event Notification configured to trigger an AWS SQS Queue whenever a new object is created (`s3:ObjectCreated:*`) in the designated raw data bucket. A Lambda function is then triggered by messages in the SQS queue.
*   **Payload:** The SQS message payload will contain details about the S3 object that triggered the event, specifically:
    *   `Bucket Name`
    *   `Object Key` (path to the raw data file)
    *   `Event Time`
*   **Purpose:** This decouples the S3 event from the processing logic, providing resilience (SQS retries) and allowing scaling.

### 2.2 Optional: Manual Trigger Endpoint (Internal/Admin)

*   **Endpoint:** `/trigger-wellness-job`
*   **Method:** `POST`
*   **Payload:**
    ```json
    {
      "s3_bucket": "your-raw-data-bucket",
      "s3_key": "path/to/client/data.json"
    }
    ```
*   **Purpose:** Allows manual triggering of the process for testing, debugging, or reprocessing specific files. This endpoint would typically be behind an API Gateway and invoke the same Step Functions workflow initiated by the SQS trigger.
*   **Response:**
    *   `200 OK`:
        ```json
        {
          "message": "Processing job initiated",
          "job_id": "step-functions-execution-arn"
        }
        ```
    *   `400 Bad Request`: If required parameters are missing.
    *   `500 Internal Server Error`: If workflow initiation fails.

## 3. Data Models

A simple data store (e.g., AWS DynamoDB) is needed to track the status of each processing job, link the input/output files, and store client contact information derived from the input data for messaging purposes.

### 3.1 `ProcessingJob` Table (DynamoDB Example)

*   **Purpose:** Track the status and metadata for each client data processing request.
*   **Partition Key:** `job_id` (String, e.g., a UUID or the Step Functions execution ARN)
*   **Attributes:**
    *   `job_id` (String): Unique identifier for the processing job.
    *   `input_s3_key` (String): S3 key of the original raw client data file.
    *   `output_s3_key` (String): S3 key of the generated PDF plan file (populated upon completion).
    *   `client_email` (String): Client's email address extracted from input data.
    *   `client_whatsapp` (String): Client's WhatsApp contact number extracted from input data.
    *   `status` (String): Current status of the job (e.g., `PENDING`, `FETCHING_DATA`, `GENERATING_PLAN`, `GENERATING_PDF`, `UPLOADING_PDF`, `SENDING_EMAIL`, `SENDING_WHATSAPP`, `COMPLETED`, `FAILED`).
    *   `start_time` (String): ISO 8601 timestamp when the job started.
    *   `completion_time` (String): ISO 8601 timestamp when the job completed (success or failure).
    *   `error_details` (String): Details if the job failed.
    *   `client_name` (String): Client's Full Name extracted from input data.

## 4. Business Logic

The core business logic will be orchestrated using AWS Step Functions to create a robust, stateful workflow. Each step in the workflow will be a separate AWS Lambda function responsible for a single task.

### 4.1 Workflow Steps (AWS Step Functions)

1.  **`StartProcessing` (Lambda or Passthrough state):** Initiated by the SQS-triggered Lambda or the manual trigger endpoint. Receives the S3 object details. Creates an entry in the `ProcessingJob` DynamoDB table with status `PENDING`. Passes S3 details and `job_id` to the next step.
2.  **`FetchDataFromS3` (Lambda):**
    *   **Input:** S3 bucket and key (`input_s3_key`).
    *   **Process:** Reads the content of the JSON file from the specified S3 location. Parses the JSON data. Extracts key client info (`Email`, `WhatsApp Contact Number`, `Full Name`) and updates the `ProcessingJob` entry.
    *   **Output:** Parsed client data (JSON object) and `job_id`. Updates job status to `FETCHING_DATA`.
3.  **`FormatPromptForGPT` (Lambda):**
    *   **Input:** Parsed client data (JSON object).
    *   **Process:** Constructs the detailed prompt string required by the GPT-4o API, incorporating the persona, instructions, and the extracted client data according to the specified sections (Personal Info, Medical, Diet Habits, etc.). Handles missing data points by intelligently estimating or marking as "User Input Missing" as per prompt instructions.
    *   **Output:** Formatted prompt string and `job_id`. Updates job status to `FORMATTING_PROMPT`.
4.  **`CallOpenAIGPT4o` (Lambda):**
    *   **Input:** Formatted prompt string and `job_id`.
    *   **Process:** Calls the OpenAI GPT-4o Chat Completion API with the prompt. Retrieves the API key from AWS Secrets Manager. Implements retry logic for transient API errors.
    *   **Output:** The plain text response from the GPT-4o API (the generated plan) and `job_id`. Updates job status to `GENERATING_PLAN`.
5.  **`GeneratePlanPDF` (Lambda):**
    *   **Input:** Plain text plan from GPT-4o and `job_id`.
    *   **Process:** Uses a PDF generation library (e.g., ReportLab in Python, or calls a service like AWS Step Functions integrates with third-party APIs or uses a containerized service) to format the plain text plan into a structured PDF document. Adds headings, tables (for meal plan, routine, grocery), and formats the content neatly.
    *   **Output:** The generated PDF content (binary data) and `job_id`. Updates job status to `GENERATING_PDF`.
6.  **`UploadPDFToS3` (Lambda):**
    *   **Input:** PDF content (binary data), `job_id`, and desired output S3 bucket/prefix.
    *   **Process:** Uploads the PDF content to the designated output S3 bucket (e.g., `your-plan-pdfs-bucket`) using a predictable key (e.g., `plans/<job_id>/wellness_plan.pdf`).
    *   **Output:** The S3 URI or key of the uploaded PDF (`output_s3_key`) and `job_id`. Updates the `ProcessingJob` entry with `output_s3_key` and status to `UPLOADING_PDF`.
7.  **`SendEmailNotification` (Lambda):**
    *   **Input:** `job_id`, `client_email`, `client_name`, `output_s3_key`.
    *   **Process:** Uses AWS SES (Simple Email Service) or an SNS topic triggering another Lambda to send an email to the client. Includes the client's name and a link to the generated PDF in S3 (ensure S3 object is public or pre-signed URL is generated if required, based on security policy). Attaching the PDF directly is also an option depending on size limits and service capabilities.
    *   **Output:** Success/Failure status for email sending and `job_id`. Updates job status to `SENDING_EMAIL`.
8.  **`SendWhatsAppMessage` (Lambda):**
    *   **Input:** `job_id`, `client_whatsapp`, `client_name`, `output_s3_key`.
    *   **Process:** Uses a WhatsApp Business API provider (e.g., Twilio, MessageBird) to send a WhatsApp message to the client. Retrieves API credentials from Secrets Manager. The message should include the client's name and potentially a link to the PDF or send it as a document attachment if the API supports it.
    *   **Output:** Success/Failure status for WhatsApp sending and `job_id`. Updates job status to `SENDING_WHATSAPP`.
9.  **`CompleteJob` (Lambda or Passthrough state):**
    *   **Input:** Results from email and WhatsApp sending steps, `job_id`.
    *   **Process:** Finalizes the `ProcessingJob` entry in DynamoDB. Sets final status to `COMPLETED` if both messages were sent successfully, or `COMPLETED_WITH_ERRORS` if one failed, or `FAILED` if a critical error occurred earlier in the workflow. Records `completion_time`.
    *   **Output:** Final job status.

### 4.2 Error Handling & Retries

*   AWS Step Functions provides built-in retry mechanisms for Lambda tasks (configurable number of retries, backoff rate).
*   Specific error handling should be implemented within Lambdas (e.g., for API call failures) and propagated to Step Functions.
*   Step Functions Catch states can be used to handle specific errors (e.g., PDF generation failure, S3 upload error) and transition to a cleanup or notification step without failing the entire workflow immediately.
*   Failed jobs should be visible in the `ProcessingJob` table and CloudWatch logs for investigation.

## 5. Security

Given the sensitive nature of wellness data, security is paramount.

*   **IAM Roles:**
    *   Each Lambda function should have a minimal IAM role with *only* the permissions needed for its specific task (e.g., `FetchDataFromS3` needs `s3:GetObject`, `CallOpenAIGPT4o` needs `secretsmanager:GetSecretValue`, `UploadPDFToS3` needs `s3:PutObject`, `SendEmailNotification` needs `ses:SendEmail`, `SendWhatsAppMessage` needs `secretsmanager:GetSecretValue`).
    *   The SQS-triggering Lambda needs `sqs:DeleteMessage` and potentially `sqs:ReceiveMessage` if it's a polling model (though SQS triggers handle polling).
    *   The Step Functions execution role needs permission to invoke the Lambdas defined in the state machine.
    *   Lambdas interacting with DynamoDB need `dynamodb:PutItem`, `dynamodb:UpdateItem`, etc.
*   **Secrets Management:** API keys for OpenAI, Twilio/WhatsApp, etc., *must* be stored in a secure service like AWS Secrets Manager or AWS Systems Manager Parameter Store (using SecureString). Lambda functions should retrieve these secrets at runtime. **Never hardcode secrets.**
*   **S3 Security:**
    *   Enable Server-Side Encryption (SSE-S3 or SSE-KMS) on both the raw data S3 bucket and the generated plans S3 bucket.
    *   Use S3 Bucket Policies and IAM policies to restrict access to only the necessary roles (Lambdas, possibly admin users).
    *   If the PDF links sent via email need to be publicly accessible, configure this carefully (e.g., use CloudFront with OAI for controlled access, or generate short-lived pre-signed URLs rather than making objects truly public). Avoid making the raw data bucket public.
*   **Network Security:** Ensure Lambdas run within a VPC if they need access to resources in a private subnet (like RDS), although for this setup, only S3 and external API calls are needed, which don't strictly require a VPC unless enforcing egress filtering. Use HTTPS for all external API calls (OpenAI, Twilio).
*   **Data Retention:** Define and implement a policy for how long raw input data and generated PDF plans are stored in S3 based on privacy and compliance requirements.

## 6. Performance

While the requirement is "within 2 hours", optimizing performance improves efficiency and reduces costs.

*   **Lambda Performance:**
    *   Allocate appropriate memory to Lambda functions. More memory also allocates proportionally more CPU. Monitor execution times and CloudWatch metrics (`Duration`, `MemoryUtilization`) to tune.
    *   Use efficient libraries for JSON parsing, PDF generation, and API calls.
    *   Handle cold starts if latency becomes an issue (e.g., using Provisioned Concurrency for critical steps, though likely unnecessary for a 2-hour SLA).
*   **Step Functions:**
    *   Monitor Step Functions execution time in the AWS Management Console. Identify steps that take the longest.
    *   Design steps to be granular enough for retries but not excessively fine-grained, which adds Step Functions overhead.
*   **API Calls:**
    *   Implement exponential backoff and jitter for retries on external API calls (OpenAI, Twilio) to handle rate limits and transient network issues gracefully.
    *   Monitor API latency.
*   **S3 Operations:** Ensure efficient read/write operations, especially for potentially large JSON files or PDF files. Use appropriate S3 SDK methods.
*   **Asynchronous Processing:** The Step Functions workflow *is* inherently asynchronous, initiated by the S3 event, which is the correct approach for this type of background task.

## 7. Code Examples

Here are simplified Python code examples for key Lambda functions using the `boto3` (AWS SDK) and `openai` libraries.

### 7.1 Fetch Data from S3 Lambda (`FetchDataFromS3`)

```python
import boto3
import json
import os

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE_NAME']) # Table name from Lambda environment variable

def lambda_handler(event, context):
    # Event contains data passed from previous Step Functions state (or initial trigger)
    job_id = event['job_id']
    input_s3_key = event['input_s3_key']
    input_s3_bucket = event['input_s3_bucket'] # Assume bucket name is also passed

    try:
        # Update job status
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET #s = :status, #st = :timestamp",
            ExpressionAttributeNames={'#s': 'status', '#st': 'start_time'},
            ExpressionAttributeValues={':status': 'FETCHING_DATA', ':timestamp': json.dumps(event.get('timestamp', 'N/A'))} # Use event timestamp or current time
        )

        print(f"Fetching data from s3://{input_s3_bucket}/{input_s3_key}")
        response = s3.get_object(Bucket=input_s3_bucket, Key=input_s3_key)
        file_content = response['Body'].read().decode('utf-8')
        client_data = json.loads(file_content)

        # Extract key info for job tracking and messaging
        client_email = client_data.get("Email", "N/A").replace("mailto:", "") # Clean up mailto: prefix
        client_whatsapp = client_data.get("WhatsApp Contact Number", "N/A")
        client_name = client_data.get("Full Name", "Client")

        # Update job with contact info
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET client_email = :email, client_whatsapp = :whatsapp, client_name = :name",
            ExpressionAttributeValues={
                ':email': client_email,
                ':whatsapp': client_whatsapp,
                ':name': client_name
            }
        )

        print(f"Successfully fetched and parsed data for job {job_id}")

        # Pass data to the next step
        return {
            'statusCode': 200,
            'client_data': client_data,
            'job_id': job_id
        }

    except Exception as e:
        print(f"Error fetching data for job {job_id}: {e}")
        # Update job status to FAILED
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET #s = :status, error_details = :error, completion_time = :timestamp",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': 'FAILED',
                ':error': str(e),
                ':timestamp': json.dumps(context.get_remaining_time_in_millis()) # Simple way to get end time relative to timeout
            }
        )
        # Step Functions will catch this exception
        raise

```

### 7.2 Call OpenAI GPT-4o Lambda (`CallOpenAILambda`)

```python
import json
import os
import openai
import boto3

secretsmanager = boto3.client('secretsmanager')

# Cache the secret value outside the handler for performance
openai_api_key = None

def get_openai_api_key():
    global openai_api_key
    if openai_api_key is None:
        secret_name = os.environ['OPENAI_SECRET_NAME'] # Secret name from Lambda environment variable
        try:
            get_secret_value_response = secretsmanager.get_secret_value(
                SecretId=secret_name
            )
            # Secrets Manager returns the value as a string or binary
            if 'SecretString' in get_secret_value_response:
                secret = get_secret_value_response['SecretString']
                openai_api_key = json.loads(secret)['OPENAI_API_KEY'] # Assuming secret is JSON: {"OPENAI_API_KEY": "sk-..."}
            else:
                # Handle binary secret if necessary
                raise ValueError("Secret is not a string type")
        except Exception as e:
            print(f"Error retrieving OpenAI API key: {e}")
            raise e # Re-raise to fail the lambda and trigger Step Functions retry

    return openai_api_key

dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE_NAME']) # Table name from Lambda environment variable


def lambda_handler(event, context):
    # Event contains data passed from previous Step Functions state
    formatted_prompt = event['formatted_prompt']
    job_id = event['job_id']

    try:
        # Update job status
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': 'GENERATING_PLAN'}
        )

        api_key = get_openai_api_key()
        openai.api_key = api_key

        print(f"Calling OpenAI API for job {job_id}...")

        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o", # Use the specified model
            messages=[
                {"role": "system", "content": "You are a clinical dietician with 25+ years of experience... (Include your detailed prompt instructions here)"},
                {"role": "user", "content": formatted_prompt}
            ],
            max_tokens=4000, # Adjust based on expected plan length
            temperature=0.7  # Adjust for creativity vs consistency
        )

        plan_text = response.choices[0].message.content
        print(f"Successfully received plan from OpenAI for job {job_id}")

        # Pass the plan text to the next step
        return {
            'statusCode': 200,
            'plan_text': plan_text,
            'job_id': job_id
        }

    except Exception as e:
        print(f"Error calling OpenAI API for job {job_id}: {e}")
         # Update job status to FAILED
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET #s = :status, error_details = :error, completion_time = :timestamp",
            ExpressionAttributeNames={'#s': 'status'},
             ExpressionAttributeValues={
                ':status': 'FAILED',
                ':error': str(e),
                ':timestamp': json.dumps(context.get_remaining_time_in_millis())
            }
        )
        raise # Re-raise to trigger Step Functions retry or failure

```

### 7.3 Upload PDF to S3 Lambda (`UploadPDFToS3`)

```python
import boto3
import os
import json

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE_NAME']) # Table name from Lambda environment variable
output_bucket_name = os.environ['OUTPUT_S3_BUCKET'] # Output bucket name from Lambda environment variable

def lambda_handler(event, context):
    # Event contains data passed from previous Step Functions state
    # Assumes PDF content is passed directly (might need adjustment based on PDF generation method)
    # If PDF generation saves to /tmp, you'd read from there.
    # For simplicity, let's assume the PDF Lambda returns the content.
    pdf_content = event['pdf_content'] # Raw bytes of the PDF
    job_id = event['job_id']

    # Determine output key
    output_s3_key = f"plans/{job_id}/wellness_plan_{job_id}.pdf" # Unique key per job

    try:
        # Update job status
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': 'UPLOADING_PDF'}
        )

        print(f"Uploading PDF to s3://{output_bucket_name}/{output_s3_key} for job {job_id}")

        # Upload the PDF bytes to S3
        s3.put_object(
            Bucket=output_bucket_name,
            Key=output_s3_key,
            Body=pdf_content,
            ContentType='application/pdf',
            ServerSideEncryption='AES256' # Ensure encryption
        )

        print(f"Successfully uploaded PDF for job {job_id}")

        # Update job with output S3 key
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET output_s3_key = :output_key",
            ExpressionAttributeValues={':output_key': output_s3_key}
        )


        # Pass data to the next step (messaging)
        return {
            'statusCode': 200,
            'job_id': job_id,
            'output_s3_key': output_s3_key # Pass key for messaging
            # Client email/whatsapp/name can be retrieved from the job_id in the next step
            # or passed from previous steps if convenient
        }

    except Exception as e:
        print(f"Error uploading PDF for job {job_id}: {e}")
         # Update job status to FAILED
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression="SET #s = :status, error_details = :error, completion_time = :timestamp",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': 'FAILED',
                ':error': str(e),
                ':timestamp': json.dumps(context.get_remaining_time_in_millis())
            }
        )
        raise # Re-raise to trigger Step Functions retry or failure

```

**Note:** The PDF Generation Lambda (`GeneratePlanPDF`) is not included as a simple code example because it requires a PDF library (like ReportLab) which adds complexity (layering in Lambda, text formatting logic). Its output should be the binary content of the PDF. The `FormatPromptForGPT` logic is also complex as it involves parsing and structuring data into the specific, lengthy prompt text provided. These would be separate Lambda functions following the same pattern (read input from event, perform logic, return output for next step, update job status).

The sending Lambdas (`SendEmailNotification`, `SendWhatsAppMessage`) would use AWS SES/SNS and a third-party WhatsApp API client library respectively, retrieving recipient info and the `output_s3_key` (to generate a link or fetch the file) using the `job_id` to query the DynamoDB table.

This guide provides the architectural blueprint and core code examples for building the backend solution on AWS.
```
