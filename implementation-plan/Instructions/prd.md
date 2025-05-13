```markdown
# Wellness Plan Automation System PRD

**Version:** 1.0
**Date:** May 13, 2025

---

## 1. Executive Summary

This document outlines the requirements for a system designed to automate the creation and delivery of personalized Indian vegan diet and wellness plans. The system will ingest client wellness data stored in an AWS S3 bucket (originating from a Google Form), leverage the GPT-4o API to generate a comprehensive, personalized plan PDF based on detailed specifications, store the resulting PDF back in AWS S3, and finally deliver the PDF to the client via WhatsApp and Email within a strict 2-hour timeframe from data ingestion. This automation significantly reduces manual effort, scales plan delivery, and ensures timely, personalized support for clients.

---

## 2. Product Vision

**Purpose:** To empower individuals seeking holistic wellness by providing them with highly personalized, expert-level Indian vegan diet and lifestyle plans, delivered efficiently and automatically based on their unique health data.

**Users:** The primary users are individuals who have completed a wellness questionnaire (via Google Form), seeking a tailored plan. The system also serves internal administrators who manage the data flow and monitor system performance.

**Business Goals:**
*   Streamline the process of generating personalized wellness plans.
*   Reduce the operational cost and time associated with manual plan creation.
*   Increase the volume of clients that can be serviced.
*   Enhance client satisfaction through timely delivery of highly relevant and personalized content.
*   Position the service as innovative and technology-driven in the wellness space.

---

## 3. User Personas

**Persona:** Kavita Kapoor - The Busy Wellness Seeker

*   **Profile:** A 50-year-old female business owner from Jaipur, India. Married, with a busy, fixed work schedule. She is seeking to improve her health through structured diet and lifestyle changes. She has specific goals (weight gain, boost immunity, reduce stress, better sleep) and existing conditions/allergies (Migraine, Dust, Gluten). Not currently on medication and hasn't followed a structured plan before. Sedentary activity level.
*   **Goals:**
    *   Receive a comprehensive, personalized diet and wellness plan tailored to her specific needs, goals, and constraints (Indian, vegan, quick meals).
    *   Get the plan quickly and conveniently through accessible channels (WhatsApp, Email).
    *   Understand the plan clearly and implement it effectively.
    *   See measurable improvements in her health goals (weight, stress, sleep, energy).
*   **Pain Points:**
    *   Limited time to research or follow complex generalized plans.
    *   Difficulty finding expert advice that fits her specific dietary needs (Indian vegan) and lifestyle.
    *   Worry about adhering to a plan with existing health issues and allergies.
    *   Need for a plan that integrates diet, exercise, and stress management holistically.
    *   Frustration with generic online plans that don't address her unique situation.

---

## 4. Feature Specifications

### 4.1. Data Ingestion & S3 Storage

**Description:** The system must be able to monitor a designated AWS S3 bucket for new files containing client wellness data and extract the relevant information.

*   **User Story:**
    *   As the system, I want to automatically detect and read newly uploaded client wellness data files from a specific S3 bucket so that I can initiate the plan generation process.
*   **Acceptance Criteria:**
    *   The system successfully detects the creation of new objects (files) in the configured S3 bucket.
    *   The system can read the content of the uploaded file, assuming a structured format (e.g., JSON, or a parsed representation of the Google Form output).
    *   The system can parse the data fields according to the expected structure provided in the prompt (Email, Full Name, DOB, Gender, etc.).
    *   Extracted data is temporarily stored in memory or a temporary processing store for the next steps.
    *   Each ingestion event is logged with a unique identifier.
*   **Edge Cases:**
    *   S3 bucket is empty or new file uploads stop.
    *   Uploaded file is not in the expected format or is corrupted.
    *   File contains missing or unexpected fields.
    *   S3 access permissions are incorrect, preventing read access.
    *   The same file is uploaded multiple times.
    *   Extremely large file size causing processing issues.

### 4.2. AI Plan Generation (GPT-4o Integration)

**Description:** The system will utilize the GPT-4o API to generate the personalized wellness plan text based on the extracted client data and the detailed prompt provided.

*   **User Story:**
    *   As the system, I want to send the extracted client wellness data to the GPT-4o API using the predefined persona and prompt structure to generate a comprehensive wellness plan text.
*   **Acceptance Criteria:**
    *   The system constructs the API request to GPT-4o, including the detailed prompt specifications (Role, Expertise, Input Format handling, Deliverables sections).
    *   All relevant extracted client data fields are incorporated into the API prompt accurately, mapped to the required fields (Personal Info, Medical, Diet Habits, Lifestyle, Other Details, Nutritional Goals).
    *   The API call to GPT-4o is successful and returns a text response.
    *   The returned text response contains the content for all required deliverables: 4-Week Meal Plan, Weekly Daily Routine, Weekly Grocery Lists, DOs & DON'Ts, Stress & Balance Tips, and Summary & Follow-up.
    *   The generated content adheres to the constraints specified in the prompt (Indian vegan, quick meals, specific ingredients, quantities, mindful eating, 100% vegetarian, local context for groceries).
    *   The AI intelligently handles missing data fields as specified ("intelligently estimate" or mark as "User Input Missing").
    *   The AI output adheres to the persona and tone of a clinical dietician.
*   **Edge Cases:**
    *   GPT-4o API returns an error (e.g., authentication, rate limit, internal error).
    *   API request times out.
    *   The AI fails to follow the prompt instructions (e.g., includes non-vegan items, misses sections, asks questions).
    *   The AI output is garbled, incomplete, or malformed (e.g., JSON-like structure within text).
    *   Prompt size exceeds GPT-4o token limits (unlikely with specified data, but possible).
    *   AI generates non-relevant or harmful content (requires content filtering/moderation).

### 4.3. PDF Generation

**Description:** The system will convert the raw text output from the GPT-4o API into a structured, visually appealing PDF document.

*   **User Story:**
    *   As the system, I need to format the AI-generated wellness plan text into a clean, readable PDF document for the client.
*   **Acceptance Criteria:**
    *   A PDF document is successfully generated from the AI text output.
    *   The PDF maintains the structure requested in the prompt (sections, tables for meal plans, routines, groceries).
    *   Formatting is clean and professional (readable fonts, appropriate spacing, tables are well-aligned).
    *   The PDF includes a title and potentially the client's name for personalization.
    *   The generated PDF file size is reasonable for email and WhatsApp delivery.
*   **Edge Cases:**
    *   The AI output contains formatting inconsistencies or special characters that break PDF rendering.
    *   Tables generated by the AI are malformed or too wide for the page.
    *   PDF generation library encounters an error.
    *   Empty sections from the AI output result in blank pages or awkward formatting in the PDF.

### 4.4. PDF Storage (S3)

**Description:** The generated PDF document will be stored in a separate, designated AWS S3 bucket.

*   **User Story:**
    *   As the system, I need to store the generated PDF plan file in a specific S3 bucket for archiving and delivery purposes.
*   **Acceptance Criteria:**
    *   The generated PDF file is successfully uploaded to the configured output S3 bucket.
    *   The file name follows a logical convention (e.g., `client_email_timestamp.pdf` or `client_id_timestamp.pdf`) ensuring uniqueness.
    *   File permissions are set correctly (e.g., private, accessible only by the delivery mechanism).
    *   The storage location (S3 path) of the PDF is logged for tracking and delivery.
*   **Edge Cases:**
    *   S3 upload fails due to network issues or permissions.
    *   Naming conflict during upload (though mitigated by timestamp/unique ID).
    *   Incorrect S3 bucket configuration.

### 4.5. Plan Delivery (WhatsApp & Email)

**Description:** The system will deliver the generated PDF plan to the client using their provided WhatsApp number and Email address. This process must be completed within 2 hours of the initial data ingestion.

*   **User Story:**
    *   As the system, I want to send the generated PDF wellness plan to the client via WhatsApp and Email promptly after generation, ensuring delivery within the 2-hour SLA.
*   **Acceptance Criteria:**
    *   The system retrieves the client's WhatsApp contact number and Email address from the ingested data.
    *   The system successfully calls the WhatsApp Business API to send a message to the client with the PDF attached. The message should be personalized (e.g., "Your personalized wellness plan is ready!").
    *   The system successfully calls an Email Sending API (e.g., AWS SES, SendGrid) to send an email to the client with the PDF attached. The email subject and body should be appropriate and personalized.
    *   Both WhatsApp and Email delivery attempts are logged with timestamps and status (success/failure).
    *   The entire workflow, from S3 ingestion trigger to successful delivery confirmation for *both* channels, is completed within 2 hours.
    *   If one delivery channel fails (e.g., invalid WhatsApp number), the system still attempts the other channel and logs the failure.
*   **Edge Cases:**
    *   Invalid or unreachable WhatsApp number.
    *   Invalid or bounce-back email address.
    *   WhatsApp API or Email API service is down or returns an error.
    *   Attachment size exceeds API limits (mitigated by controlling PDF size in step 4.3).
    *   Network issues prevent delivery.
    *   Processing takes longer than 2 hours, resulting in SLA breach (needs monitoring and alerting).
    *   Client's contact information is missing in the input data.

### 4.6. System Monitoring & Error Handling

**Description:** The system needs robust logging, monitoring, and error handling capabilities to ensure reliability and meet the 2-hour SLA.

*   **User Story:**
    *   As a system administrator, I need to monitor the status of all plan generation requests, track processing times, and be alerted immediately if any request fails or is at risk of exceeding the 2-hour delivery window.
*   **Acceptance Criteria:**
    *   Comprehensive logs are generated for each step of the process (ingestion, AI call, PDF generation, S3 storage, WhatsApp delivery, Email delivery).
    *   Logs include relevant data like client ID/email, timestamps, status (success/failure), and specific error messages.
    *   A monitoring system tracks the progress and duration of each end-to-end request (from ingestion to delivery).
    *   Automated alerts are triggered if a request fails at any stage or if a request's processing time approaches/exceeds the 2-hour limit.
    *   Failed requests are handled gracefully (e.g., retries for transient errors, clear logging for persistent failures).
    *   Mechanisms are in place to re-process failed requests manually or automatically (within limits).
*   **Edge Cases:**
    *   Logging system failure prevents tracking.
    *   Monitoring system failure prevents alerts.
    *   Cascade of failures due to external API issues.
    *   Handling sensitive data in logs (ensure PII is masked or encrypted).

---

## 5. Technical Requirements

*   **APIs:**
    *   **AWS S3 API:** For detecting new objects, reading files, and uploading generated PDFs. Requires appropriate IAM roles and permissions.
    *   **OpenAI API (GPT-4o):** For generating the plan text. Requires an API key, handling API call structure (system message, user message), and managing potential rate limits.
    *   **WhatsApp Business API:** For sending the PDF via WhatsApp. Requires a configured WhatsApp Business Account, API key, and template messaging (if necessary, or direct media sending).
    *   **Email Sending API:** (e.g., AWS SES, SendGrid, Mailgun) For sending the PDF via Email. Requires API key and configuration.
*   **Data Storage:**
    *   **AWS S3:** Two distinct buckets: one for incoming raw data files and one for outgoing generated PDF files. Requires secure configuration (encryption at rest, access policies).
    *   **Database (Optional but Recommended):** A database (e.g., DynamoDB, PostgreSQL) to store metadata about each request, track processing status, timestamps, and logging information. This is crucial for monitoring, re-processing, and ensuring the 2-hour SLA.
*   **Processing Environment:**
    *   **Trigger Mechanism:** An AWS Lambda function triggered by S3 PUT events on the incoming bucket is a suitable serverless approach for data ingestion and initiating the workflow.
    *   **Workflow Management:** For managing the sequence of API calls and parallel processes (like simultaneous WhatsApp and Email sending) and tracking the 2-hour SLA, AWS Step Functions or a similar workflow orchestration service could be beneficial. Alternatively, the Lambda function could orchestrate calls directly or push messages to a queue (e.g., SQS) for subsequent processing steps handled by other Lambdas.
    *   **Compute:** Lambda functions require sufficient memory and timeout settings for API calls (especially GPT-4o, which can take time) and PDF generation. Consider containerized solutions (ECS/EKS) if processing becomes too complex or resource-intensive for Lambda limits.
*   **Timing Constraint:** The architecture must be designed to process and deliver within 2 hours. This necessitates efficient parsing, fast API calls, and potentially parallel execution of delivery methods. Monitoring the duration of each step and the total process is critical. AWS CloudWatch can monitor Lambda durations and trigger alarms.
*   **Security:**
    *   Secure storage of API keys and credentials (e.g., AWS Secrets Manager).
    *   Data encryption at rest (S3, Database) and in transit (HTTPS for all API calls).
    *   Strict access control (IAM roles) for AWS resources.
    *   Compliance with data privacy regulations (if applicable, e.g., GDPR, HIPAA, depending on client location and data type, though the prompt implies wellness data which may be sensitive).
*   **Scalability:** The architecture should be able to handle an increasing number of concurrent form submissions/S3 uploads. Serverless components (Lambda, SQS, Step Functions, DynamoDB) inherently offer scalability.
*   **Error Handling:** Implement robust try-catch blocks, API call retries (with exponential backoff), dead-letter queues (for message queues), and detailed error logging.

---

## 6. Implementation Roadmap

This roadmap outlines a phased approach to building and deploying the Wellness Plan Automation System.

**Phase 1: Foundation & Core AI Integration (Est. 4-6 Weeks)**

*   **Goal:** Establish data ingestion, core processing logic, and basic error handling. Get data in -> send to AI -> receive text -> log outcome.
*   **Features:**
    *   Setup AWS S3 Buckets (Incoming & Outgoing).
    *   Implement S3 Event Trigger (Lambda).
    *   Develop Data Parsing Logic (from S3 file format).
    *   Implement GPT-4o API Integration:
        *   Construct the detailed prompt dynamically with client data.
        *   Make the API call.
        *   Receive and parse the text response.
    *   Implement Basic Logging for Ingestion, AI Call, and Processing Status.
    *   Develop Skeleton Error Handling (log errors, but no automated retries yet).
*   **Milestones:** Successfully ingest data, call GPT-4o, receive *any* text response, and log the process.

**Phase 2: PDF Generation & Initial Delivery Channel (Est. 3-4 Weeks)**

*   **Goal:** Convert AI output to PDF and enable delivery via one channel (Email first, often simpler).
*   **Features:**
    *   Develop PDF Generation Logic (using a library like ReportLab, wkhtmltopdf, etc.). This involves mapping structured text output from AI into PDF sections and tables.
    *   Implement PDF Storage to the Outgoing S3 bucket.
    *   Implement Email Delivery using an Email Sending API (e.g., AWS SES):
        *   Retrieve client email.
        *   Attach PDF from S3.
        *   Send personalized email.
        *   Log delivery status.
*   **Milestones:** Successfully generate PDF from AI output, store it in S3, and send it via Email.

**Phase 3: WhatsApp Delivery, SLA Enforcement & Monitoring (Est. 4-5 Weeks)**

*   **Goal:** Add the second delivery channel, implement the 2-hour time constraint logic, and build robust monitoring.
*   **Features:**
    *   Implement WhatsApp Delivery using WhatsApp Business API:
        *   Retrieve client WhatsApp number.
        *   Implement API call for sending PDF attachment.
        *   Log delivery status.
    *   Develop 2-hour SLA Monitoring:
        *   Track the start time (S3 ingestion).
        *   Track completion time (successful delivery via *both* channels).
        *   Implement logic to check if 2 hours are exceeded.
    *   Implement Automated Alerting (e.g., via CloudWatch Alarms, SNS) for:
        *   Failed steps (AI error, PDF generation error, delivery error).
        *   Requests exceeding the 2-hour window.
    *   Refine Error Handling: Add automated retries for transient API errors. Implement a dead-letter queue for persistent failures.
    *   Refine PDF Formatting based on testing and review.
*   **Milestones:** Successfully deliver via both Email and WhatsApp. Implement real-time monitoring of request duration and trigger alerts for failures/SLA breaches.

**Phase 4: Optimization, Robustness & Maintenance (Ongoing)**

*   **Goal:** Improve performance, cost-efficiency, handle edge cases more gracefully, and establish ongoing operational processes.
*   **Features:**
    *   Performance Tuning (e.g., optimize PDF generation speed, AI call efficiency if possible).
    *   Cost Optimization (e.g., analyze Lambda duration/memory, S3 storage costs, API costs).
    *   Further Edge Case Handling (e.g., invalid data formats that break parsing, missing contact info).
    *   Implement a dashboard or reporting mechanism for monitoring request status and performance metrics.
    *   Establish procedures for handling alerted failures and re-processing requests.
    *   Ongoing monitoring and maintenance of APIs and infrastructure.

---
```
