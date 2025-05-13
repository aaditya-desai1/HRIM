Okay, here is the system flow documentation for the wellness plan generation and delivery system, formatted in markdown as requested.

```markdown
# Solution Architecture Flow Documentation: Automated Wellness Plan Generation & Delivery

## 1. Document Header

*   **Version:** 1.0
*   **Date:** May 13, 2025

## 2. System Overview

This document outlines the architecture and processes for an automated system designed to generate personalized wellness plans based on client data submitted via a Google Form (data assumed to be stored in AWS S3). The system leverages AWS services and the OpenAI GPT-4o API to process the data, generate a comprehensive plan in PDF format, and deliver it to the client via WhatsApp and Email within a specified timeframe.

**Key Components:**

*   **AWS S3:** Acts as the central storage for raw client data (input) and generated wellness plan PDFs (output).
*   **AWS Lambda:** Serverless compute service triggered by new data arriving in S3. It orchestrates the data fetching, processing (calling GPT-4o), PDF generation, and delivery steps.
*   **OpenAI GPT-4o API:** Provides the core intelligence for analyzing client data and generating the personalized wellness plan content based on a detailed prompt.
*   **PDF Generation Service/Library:** A component (either within the Lambda function or a separate service) responsible for formatting the structured text output from GPT-4o into a professional PDF document.
*   **WhatsApp API:** An external service used to send the generated PDF document as a message to the client's provided WhatsApp number.
*   **Email Service (e.g., AWS SES, SendGrid):** An external or AWS service used to send the generated PDF document as an email attachment to the client's provided email address.
*   **AWS Secrets Manager:** Securely stores API keys and credentials for external services (GPT-4o, WhatsApp, Email).
*   **AWS CloudWatch:** Used for monitoring Lambda execution, logging, and setting up alarms for errors.

## 3. User Workflows

The system is primarily event-driven, triggered by the completion of a Google Form and the subsequent storage of data in S3. The "user" in this context is the client who filled out the form.

**Primary Workflow: Wellness Plan Generation & Delivery**

1.  **Client completes Google Form:** User fills out the wellness data form.
2.  **Data lands in S3:** The Google Form data (simulated as a JSON file based on the form response) is stored in a designated S3 bucket.
3.  **S3 Event Trigger:** S3 bucket configured to trigger an AWS Lambda function upon creation of a new object in the input path.
4.  **Lambda Execution:** The designated Lambda function starts.
5.  **Data Fetch:** Lambda reads the newly uploaded JSON file from S3.
6.  **GPT-4o Processing:** Lambda extracts relevant data fields, constructs the prompt including the client's data, and calls the OpenAI GPT-4o API.
7.  **Plan Generation:** GPT-4o processes the request and returns the structured text content of the personalized wellness plan.
8.  **PDF Creation:** Lambda (or an invoked helper function/service) takes the text output and formats it into a PDF document according to the specified structure (meal plan tables, routines, lists, etc.).
9.  **PDF Storage:** The generated PDF is uploaded to a designated output path in the same or a different S3 bucket.
10. **Delivery Trigger:** Lambda initiates the delivery process.
11. **WhatsApp Delivery:** Lambda calls the WhatsApp API, providing the client's number and the S3 URL (or byte stream) of the generated PDF.
12. **Email Delivery:** Lambda calls the Email Service API, providing the client's email address and the S3 URL (or byte stream) of the generated PDF as an attachment.
13. **Completion:** The Lambda function finishes execution.

**Mermaid Diagram: Primary User Workflow (from System Trigger)**

```mermaid
graph TD
    A[Client fills Google Form] --> B[Data stored in S3 <br> (Input Bucket)];
    B -- ObjectCreated Event --> C[AWS Lambda Function <br> (Plan Generator)];
    C -- Read Data --> B;
    C -- Call API <br> (Data + Prompt) --> D[OpenAI GPT-4o API];
    D -- Return Plan Content (Text) --> C;
    C -- Generate PDF --> E[PDF Generation Logic];
    E -- Output PDF --> C;
    C -- Store PDF --> F[AWS S3 <br> (Output Bucket)];
    C -- Call API (PDF) --> G[WhatsApp API];
    C -- Call API (PDF) --> H[Email Service];
    G -- Deliver Plan --> I[Client's WhatsApp];
    H -- Deliver Plan --> J[Client's Email Inbox];
```

## 4. Data Flows

This section details the movement of data between the system components.

**Data Flow Steps:**

1.  **Google Form -> S3:** Client-submitted form data is structured (e.g., as JSON) and uploaded to a specific S3 bucket (e.g., `wellness-data-input/`).
    *   *Data:* JSON object containing client wellness details.
2.  **S3 -> AWS Lambda:** Lambda function reads the JSON object from the S3 input bucket.
    *   *Data:* JSON object (client wellness details).
3.  **AWS Lambda -> OpenAI GPT-4o API:** Lambda constructs an API request including the client's data (either embedded in the prompt or via function call arguments, depending on API usage pattern) and the detailed plan generation prompt text.
    *   *Data:* API Request (contains client data, prompt text, model parameters).
4.  **OpenAI GPT-4o API -> AWS Lambda:** GPT-4o processes the request and returns the generated wellness plan content as structured text (e.g., markdown, JSON, or plain text formatted according to the prompt).
    *   *Data:* API Response (contains structured text content of the plan).
5.  **AWS Lambda -> PDF Generation Logic:** The text content received from GPT-4o is passed to the PDF generation code.
    *   *Data:* Structured text content of the wellness plan.
6.  **PDF Generation Logic -> AWS Lambda:** The PDF generation code outputs the complete plan as a PDF byte stream or file object.
    *   *Data:* PDF byte stream/file.
7.  **AWS Lambda -> S3:** The generated PDF byte stream/file is uploaded to a specific S3 bucket (e.g., `wellness-plan-output/`).
    *   *Data:* PDF file.
8.  **AWS Lambda -> WhatsApp API:** Lambda initiates an API call to the WhatsApp Business API (or similar service), providing the client's phone number and the PDF content (either directly as bytes or potentially an S3 pre-signed URL if the API supports it).
    *   *Data:* API Request (recipient number, PDF data/URL, message template if used).
9.  **AWS Lambda -> Email Service:** Lambda initiates an API call to the chosen Email Service, providing the client's email address, subject, body, and the PDF content as an attachment (either directly as bytes or potentially read from the S3 output location).
    *   *Data:* API Request (recipient email, sender email, subject, body text, PDF attachment data/URL).

**Mermaid Diagram: Detailed Data Flow**

```mermaid
graph LR
    A[S3 <br> (Input Data)] --> B[AWS Lambda];
    B -- Read JSON --> A;
    B -- Call API <br> (Prompt + Data) --> C[OpenAI GPT-4o API];
    C -- Return Text Plan Content --> B;
    B -- Pass Content --> D[PDF Generation Logic];
    D -- Output PDF Bytes --> B;
    B -- Upload PDF --> E[S3 <br> (Output Plans)];
    B -- Call API <br> (Recipient #, PDF) --> F[WhatsApp API];
    B -- Call API <br> (Recipient Email, PDF) --> G[Email Service];
```

## 5. Error Handling

Robust error handling is critical for reliability.

*   **S3 Trigger Failure:** Monitor CloudWatch logs for S3 event delivery failures. Configuration errors in S3 event notifications need manual correction.
*   **Lambda Execution Errors:**
    *   **Timeouts:** Lambda function may time out if processing (especially API calls or PDF generation) takes too long. Optimize code, increase timeout limit (up to 15 mins), consider breaking down tasks (e.g., separate Lambda for PDF generation triggered by an SQS queue).
    *   **Permissions Errors:** Lambda's IAM role must have correct permissions (S3 read/write, Secrets Manager read, network access for API calls). Monitor CloudWatch logs.
    *   **Code Errors:** Implement comprehensive `try...catch` blocks. Log detailed error information to CloudWatch Logs.
    *   **Resource Limits:** Ensure Lambda memory and ephemeral storage are sufficient.
*   **S3 Read/Write Errors:** Handle potential exceptions when reading the input JSON or writing the output PDF. Implement retry logic for transient S3 errors.
*   **OpenAI GPT-4o API Errors:**
    *   **Rate Limits:** Implement retry logic with exponential backoff. Use SQS queue between Lambda and API call if high volume is expected.
    *   **API Errors (e.g., Invalid Request, Server Error):** Log the error details returned by the API. Depending on the error type, a retry might be appropriate, or the specific record might need to be flagged for manual review.
    *   **Timeout:** Handle API call timeouts.
*   **PDF Generation Errors:** Handle errors during the PDF creation process (e.g., malformed input text from GPT-4o, library issues). Log errors and potentially save the raw GPT output for debugging.
*   **WhatsApp API Errors:** Handle errors from the WhatsApp API (e.g., invalid phone number format, delivery issues, API service errors). Log errors. Implement retries for transient errors. Failed deliveries might require notification or manual follow-up.
*   **Email Service Errors:** Handle errors from the Email Service (e.g., invalid email address, sending quota exceeded). Log errors. Implement retries. Bounce/complaint notifications should be configured and monitored.
*   **Asynchronous Processing & Dead-Letter Queues (DLQ):** Configure a DLQ for the Lambda function. If a Lambda invocation fails persistently after retries, the event is sent to the DLQ (e.g., an SQS queue). A separate process or manual intervention can then inspect messages in the DLQ to understand the failure cause and potentially reprocess them.
*   **Monitoring and Alerting:** Set up CloudWatch dashboards and alarms for Lambda error rates, duration, throttles, S3 put/get errors, and potentially external API call success/failure metrics if available. Use SNS to send notifications for critical alarms.

## 6. Security Flows

Security is paramount when dealing with sensitive client health data.

*   **Data at Rest:**
    *   **S3 Encryption:** All S3 buckets storing input data and output PDFs must have Server-Side Encryption enabled (SSE-S3 or SSE-KMS).
*   **Data in Transit:**
    *   **HTTPS:** All communication with external APIs (GPT-4o, WhatsApp, Email Service) and AWS services (S3, Secrets Manager) must use HTTPS to ensure data is encrypted in transit.
*   **Authentication and Authorization (AWS):**
    *   **IAM Roles:** The Lambda function must assume an IAM role with the principle of least privilege. This role should *only* have permissions necessary for its tasks:
        *   `s3:GetObject` on the specific input bucket/path.
        *   `s3:PutObject` on the specific output bucket/path.
        *   `secretsmanager:GetSecretValue` to retrieve API keys.
        *   `logs:CreateLogStream`, `logs:PutLogEvents` for CloudWatch logging.
        *   Network permissions to call external APIs (if in a VPC).
    *   **S3 Bucket Policies:** Configure bucket policies to strictly control access. Only the Lambda IAM role should have read access to input data and write access to output data. Access from external sources (like the original Google Form integration, if applicable) should be secured appropriately (e.g., via temporary credentials, specific IAM users/roles).
*   **Authentication and Authorization (External APIs):**
    *   **API Keys/Credentials:** OpenAI, WhatsApp, and Email Service API keys/tokens are sensitive.
    *   **Secure Storage:** Store API keys *only* in a secure secrets management service like AWS Secrets Manager. **Never hardcode credentials in code or store them in environment variables directly.**
    *   **Access by Lambda:** The Lambda function retrieves the necessary secrets from Secrets Manager at runtime using its IAM role permissions.
*   **Input Data Validation:** While the prompt asks *not* to ask follow-up questions, basic validation within the system processing might be needed to prevent crashes (e.g., check if critical fields like email/phone number exist before attempting delivery). However, strict *data* validation should be minimized to adhere to the "use all input exactly as given" constraint.
*   **Output PDF Security:** The generated PDF contains sensitive PII. Ensure the output S3 bucket is private and access is restricted. Consider if any additional measures like password protection on the PDF are necessary (though this adds complexity for the user).
*   **Monitoring Access:** Monitor access logs for S3 buckets (`Server Access Logging` or `CloudTrail Data Events`) and CloudTrail logs for Lambda execution and Secrets Manager access to detect any unauthorized activity.
```
