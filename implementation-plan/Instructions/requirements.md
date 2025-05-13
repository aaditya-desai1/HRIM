Okay, here is the detailed requirements document in markdown format, outlining the specifications for the proposed solution.

```markdown
# Requirement Document: Automated Personalized Wellness Plan Generator

**Document Header**
*   Version: 1.0
*   Date: May 13, 2025

---

## 1. Project Overview

**1.1. Purpose**
The purpose of this project is to automate the process of generating personalized wellness and diet plans for clients based on data collected via a Google Form. The system will retrieve client data stored on AWS S3, process it using the OpenAI GPT-4o API according to a highly specific prompt, generate a comprehensive wellness plan in PDF format, store the generated PDF back on S3, and deliver it to the client via WhatsApp and email within a specified timeframe. This aims to streamline the wellness plan delivery process, enhance personalization, and reduce manual effort.

**1.2. Goals**
*   Automate the extraction of client wellness data from AWS S3.
*   Leverage AI (GPT-4o) to generate personalized, comprehensive Indian vegan diet and wellness plans.
*   Generate the wellness plan in a structured PDF format.
*   Securely store generated wellness plan PDFs on AWS S3.
*   Ensure timely delivery of the generated wellness plan PDF to the client via WhatsApp and Email within 2 hours of data availability.
*   Provide a scalable and reliable solution for processing client submissions.

**1.3. Target Users**
*   **Clients:** Individuals who fill out the Google Form and receive the personalized wellness plan.
*   **Administrators:** Personnel responsible for setting up, monitoring, and maintaining the system.

---

## 2. Functional Requirements

This section details the specific functions the system must perform.

**F-001: Data Ingestion Trigger & Retrieval**
*   **Description:** The system must detect new Google Form submissions (as stored/made available on AWS S3) and initiate the processing workflow for each new submission. It must then retrieve the corresponding client data file from the specified S3 location.
*   **Acceptance Criteria:**
    *   The system successfully identifies new client data entries available on S3.
    *   The system successfully reads and accesses the data file (e.g., JSON, CSV, or linked source) for a new submission from the configured S3 bucket and path.
    *   The system handles multiple concurrent new submissions.

**F-002: Data Extraction and Parsing**
*   **Description:** The system must parse the retrieved client data file and accurately extract all required fields as specified in the GPT prompt instructions (Personal Info, Medical, Diet Habits, Lifestyle, Other Details).
*   **Acceptance Criteria:**
    *   All specified fields (Full Name, DOB, Gender, etc.) are correctly identified and extracted from the input data structure.
    *   Missing required fields are detected.
    *   The system intelligently estimates missing fields or marks them as "User Input Missing: [Field]" as per the GPT prompt instruction.

**F-003: AI Prompt Formulation**
*   **Description:** The system must dynamically construct the complete prompt for the GPT-4o API using the extracted and processed client data, strictly following the structure and content provided in the User's detailed GPT prompt instructions (including role, purpose, input format, deliverables, DO NOTs).
*   **Acceptance Criteria:**
    *   A valid text prompt is generated, incorporating all extracted client data points into the specified prompt structure.
    *   The prompt includes the specified Persona (Clinical Dietician, 25+ yrs experience, US FDA, Indian vegan nutrition specialist).
    *   The prompt includes the required deliverables section structure.
    *   The prompt adheres to all negative constraints ("Do not ask follow-up questions," "Do not skip," etc.).

**F-004: GPT-4o API Call**
*   **Description:** The system must securely call the OpenAI GPT-4o API with the formulated prompt and handle the API response.
*   **Acceptance Criteria:**
    *   The system successfully establishes a connection with the OpenAI GPT-4o API.
    *   The prompt is sent correctly via the API.
    *   A response is received from the API.
    *   The system handles potential API errors (e.g., timeout, rate limits, service unavailability).

**F-005: Response Parsing and Content Structuring**
*   **Description:** The system must parse the text response received from the GPT-4o API and structure its content into the defined sections required for the PDF (4-Week Meal Plan, Weekly Routine Charts, Weekly Grocery Lists, DOs & DON'Ts, Stress & Balance Tips, Summary & Follow-up). It must ensure all generated sections match the structure and details required by the GPT prompt's deliverables.
*   **Acceptance Criteria:**
    *   The API text response is successfully parsed.
    *   All required content sections (Meal Plans Weeks 1-4, Routine, Grocery Lists Weeks 1-4, DOs/DON'Ts, Stress/Balance Tips Weeks 1-4, Summary) are identified and extracted from the text.
    *   Table structures (Meal Plans, Routine, Grocery Lists) are correctly interpreted from the text response.
    *   Quantities for 1-person and Family (4 servings) are extracted for meal plans.
    *   Quantities for grocery items are extracted.

**F-006: PDF Generation**
*   **Description:** The system must generate a professional PDF document containing the structured content parsed from the GPT-4o response. The PDF should include all the sections specified in the GPT prompt deliverables, formatted clearly with headings, tables, and lists.
*   **Acceptance Criteria:**
    *   A valid PDF file is created.
    *   The PDF includes all required sections: 4-Week Meal Plan (Tables for Wk 1-4), Weekly Daily Routine Chart (Table), Weekly Grocery Lists (Lists for Wk 1-4), DOs & DON'Ts, Stress & Balance Tips (per week), Summary & Follow-up.
    *   Tables (Meal Plan, Routine) and lists (Grocery, Tips) are correctly formatted within the PDF.
    *   The PDF is readable and well-organized.

**F-007: S3 Storage (Output)**
*   **Description:** The system must upload the newly generated wellness plan PDF file to a designated output location within the AWS S3 bucket.
*   **Acceptance Criteria:**
    *   The generated PDF file is successfully uploaded to the specified S3 bucket and folder.
    *   The file naming convention is logical (e.g., includes client name and date).
    *   File integrity is maintained during upload.

**F-008: WhatsApp API Integration and Sending**
*   **Description:** The system must integrate with a WhatsApp Business API (or similar) and send the generated wellness plan PDF as a document attachment to the client's WhatsApp contact number extracted from the input data.
*   **Acceptance Criteria:**
    *   The system successfully authenticates with the WhatsApp API.
    *   The generated PDF is sent as a document attachment to the correct WhatsApp number.
    *   A confirmation or status of the sending attempt is logged.

**F-009: Email Sending**
*   **Description:** The system must send an email to the client's email address extracted from the input data, with the generated wellness plan PDF attached.
*   **Acceptance Criteria:**
    *   The system successfully connects to the configured email service.
    *   An email is sent to the correct client email address.
    *   The generated PDF is attached to the email.
    *   The email includes a relevant subject line and body text (e.g., "Your Personalized Wellness Plan").
    *   A confirmation or status of the sending attempt is logged.

**F-010: Timely Delivery Constraint**
*   **Description:** The entire process from data ingestion (F-001) through sending via WhatsApp (F-008) and Email (F-009) must be completed within a maximum of 2 hours for each client submission.
*   **Acceptance Criteria:**
    *   For 95% of submissions under normal operating load, the timestamp of successful WhatsApp and Email delivery attempts is within 2 hours of the data ingestion timestamp.

**F-011: Error Handling and Notification**
*   **Description:** The system must detect and handle errors gracefully at each stage of the workflow (S3 retrieval, data parsing, API call, PDF generation, S3 upload, sending). It must log detailed error information and notify designated administrators.
*   **Acceptance Criteria:**
    *   System logs errors with relevant details (timestamp, error type, client ID/submission).
    *   Administrators are notified via a configured channel (e.g., email, messaging) when errors occur that prevent successful plan generation or delivery.
    *   The system attempts retries for transient errors (e.g., API call failures).

---

## 3. Non-Functional Requirements

This section describes how well the system performs its functions.

**3.1. Performance**
*   **Processing Speed:** The core processing (F-001 to F-009) must meet the 2-hour delivery constraint (F-010).
*   **Throughput:** The system should be able to handle a defined number of submissions per unit of time (e.g., X submissions per hour) while meeting the performance and timing constraints. (Specific number to be defined based on expected volume).
*   **Scalability:** The system architecture should be designed to scale horizontally to accommodate increased submission volume over time.

**3.2. Security**
*   **Data Encryption:** All client data (input, output PDF) must be encrypted at rest (on S3) and in transit (during retrieval, API calls, and sending via email/WhatsApp APIs).
*   **Access Control:** Strict access control mechanisms must be in place for accessing S3 buckets (both input and output), API keys for GPT-4o, WhatsApp, and email services. Access should be limited to necessary system components and authorized personnel.
*   **Data Privacy:** The system must handle sensitive health and personal data in compliance with relevant data protection regulations (consider local Indian data protection laws).
*   **API Key Management:** API keys and secrets must be stored and managed securely (e.g., using AWS Secrets Manager).

**3.3. Reliability**
*   **Availability:** The system should target high availability (e.g., 99.5% uptime).
*   **Resilience:** The system should be resilient to transient failures in external services (S3, APIs) through mechanisms like retries and circuit breakers.
*   **Data Integrity:** Ensure the integrity of client data throughout the process and the integrity of the generated PDF.

**3.4. Maintainability**
*   **Logging and Monitoring:** Comprehensive logging of all system activities, processing statuses, and errors is required. Monitoring tools should provide visibility into system health, performance, and processing queues.
*   **Configuration:** External dependencies (S3 paths, API keys, email/WhatsApp endpoints) and system parameters should be easily configurable without code changes.

---

## 4. Dependencies and Constraints

**4.1. Dependencies**
*   **AWS S3:** Required for storing input data (from Google Forms) and output PDF files.
*   **Google Forms:** The data source; requires a mechanism to export/sync submission data to AWS S3 in a structured format.
*   **OpenAI GPT-4o API:** The core AI model for generating the wellness plan content. Requires an active subscription and API access.
*   **WhatsApp Business API (or similar):** Required for sending the PDF via WhatsApp. Requires setup and approval.
*   **Email Sending Service:** Required for sending the PDF via email (e.g., SMTP server, SendGrid, AWS SES).
*   **Input Data Format:** The system is dependent on the specific format (e.g., JSON, CSV) and structure of the data file uploaded to S3 from the Google Form. Changes to the form structure will require system updates.
*   **Third-Party API Availability:** System performance and reliability are dependent on the availability and performance of the OpenAI, WhatsApp, and Email APIs.

**4.2. Constraints**
*   **Strict Prompt Adherence:** The system must use the *exact* provided GPT prompt structure and content for generating the plan. No deviation or asking clarifying questions is allowed by the prompt's rules.
*   **2-Hour Delivery Window:** This is a hard time limit for completing processing and sending.
*   **Output Format:** The output must be a PDF document containing all specified sections.
*   **No Follow-up Questions:** As per the GPT prompt, the system cannot interactively ask the user for missing information. It must handle missing data based on the prompt's instructions.
*   **Vegan Constraint:** The generated diet plan must strictly be 100% vegan Indian cuisine as per the prompt.

---

## 5. Risk Assessment

**5.1. Risk Identification and Mitigation**

| Risk ID | Description                      | Likelihood | Impact | Mitigation Strategy                                                                                                |
| :------ | :------------------------------- | :--------- | :----- | :----------------------------------------------------------------------------------------------------------------- |
| R-001   | External API Failure (GPT, WA, Email) | Medium     | High   | Implement retry mechanisms; Robust error logging and alerting; Monitor API status; Have contingency plans if possible (e.g., queue failed sends). |
| R-002   | S3 Access/Connectivity Issues    | Low        | High   | Monitor S3 service health; Ensure correct IAM permissions and network configuration; Implement retry logic for S3 operations. |
| R-003   | Poor Quality/Missing Input Data  | Medium     | Medium | Implement robust parsing logic; Handle missing data according to prompt rules (estimation/marking); Potentially add input data validation checks prior to processing if feasible. |
| R-004   | GPT Prompt Misinterpretation       | Low        | High   | Rigorous testing with diverse input data; Monitoring generated PDFs for content quality/accuracy; Acknowledge this inherent AI risk. |
| R-005   | Failure to Meet 2-Hour Deadline  | Medium     | High   | Performance monitoring; Queue management; Scalable infrastructure design; Prioritize processing of new submissions; Optimize processing steps. |
| R-006   | Security/Data Privacy Breach     | Medium     | Critical | Implement end-to-end encryption; Strict access controls (IAM, network); Secure API key management; Regular security audits; Compliance review. |
| R-007   | Increased API Costs              | Low        | Medium | Monitor API usage and costs; Implement usage quotas if necessary; Optimize API calls (e.g., minimum retries).         |
| R-008   | Google Form Data Link to S3 Fails | Medium     | High   | Monitor the mechanism that transfers data from Google Forms to S3; Ensure reliability of this external link/process. |
| R-009   | PDF Generation Errors            | Low        | Medium | Use a reliable PDF generation library; Handle unexpected characters or formatting from GPT output; Log generation errors. |

---
```
