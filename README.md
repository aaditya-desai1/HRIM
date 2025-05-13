# HRIM: Health & Wellness Report Implementation Manager

An automated system for generating personalized wellness plans using AWS serverless architecture and OpenAI GPT-4o.

## Overview

HRIM automates the process of generating personalized wellness and diet plans for clients based on data collected via Google Forms. The system:

1. Retrieves client data stored on AWS S3
2. Processes it using the OpenAI GPT-4o API
3. Generates a comprehensive wellness plan in PDF format
4. Stores the generated PDF back on S3
5. Delivers it to the client via WhatsApp and email within 2 hours

## Technical Architecture

- **Backend**: AWS Lambda functions written in Python
- **Workflow Orchestration**: AWS Step Functions
- **Data Storage**: AWS S3 for raw data and generated PDFs, DynamoDB for job tracking
- **AI**: OpenAI GPT-4o API for generating personalized wellness content
- **Communication**: WhatsApp Business API and AWS SES for PDF delivery

## Repository Structure

```
HRIM/
├── docs/              # Project documentation
├── src/               # Source code
│   └── lambda/        # Lambda functions for each processing step
│       ├── trigger_processor/ # Handles S3 events and starts the workflow
│       ├── fetch_data/        # Retrieves client data from S3
│       ├── format_prompt/     # Prepares data for the OpenAI API
│       ├── call_openai/       # Calls the OpenAI API and handles response
│       ├── generate_pdf/      # Creates PDF from the OpenAI response
│       ├── upload_pdf/        # Uploads the PDF to S3
│       ├── send_email/        # Sends the PDF via email
│       ├── send_whatsapp/     # Sends the PDF via WhatsApp
│       └── complete_job/      # Updates job status and handling completion
├── terraform/         # Infrastructure as code (Terraform)
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure AWS credentials
4. Deploy infrastructure using Terraform:
   ```
   cd terraform
   terraform init
   terraform apply
   ```

## Configuration

Create a `.env` file with the following variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `WHATSAPP_API_KEY`: Your WhatsApp Business API key
- Other AWS configuration is handled through IAM roles

## Local Testing Without External APIs

For local development and testing without requiring actual API keys or AWS resources, you can use the provided test tools:

### Simple Workflow Test

The `test_workflow.py` script provides a simple end-to-end test of the workflow logic without requiring any external services:

```bash
./test_workflow.py
```

This script:
1. Loads the sample client data from `test-data/sample-form-submission.json`
2. Simulates the workflow steps with mock implementations
3. Generates a text file representing the PDF output
4. Simulates delivery notifications

### Simplified Testing With Core Functionality

For an even simpler test that focuses just on the core functionality without Lambda functions, use the `simple_test.py` script:

```bash
python3 simple_test.py
```

This script:
1. Loads the sample client data
2. Formats a prompt for wellness plan generation
3. Simulates an OpenAI API response
4. Generates an actual PDF (using xhtml2pdf)
5. Creates mock email and WhatsApp delivery files
6. Saves all output to the `test_output` directory for verification

This is the recommended approach for quickly testing the core functionality without dealing with AWS service mocks.

### Testing with Real AWS SES

AWS SES offers a free tier that allows 62,000 outgoing messages per month when sent from an Amazon EC2 instance. To test email delivery with real AWS SES:

1. Verify your sender email address in the AWS SES console
2. Configure your AWS credentials using `aws configure`
3. Set the sender email as an environment variable:
   ```bash
   export SENDER_EMAIL=your-verified-email@example.com
   ```
4. Run the SES test script:
   ```bash
   ./test_ses_delivery.py
   ```

This script will:
- Generate a sample wellness plan
- Create a placeholder PDF file
- Send a real email with the PDF attachment using AWS SES
- Log the results and SES Message ID if successful

### Mock Implementations for External Services

For testing other components, mock implementations are provided in the `src/lambda/mocks/` directory:

- `mock_openai.py`: Simulates OpenAI API responses
- `mock_email.py`: Captures email sending for verification (when not using real SES)
- `mock_whatsapp.py`: Logs WhatsApp messages instead of sending them
- `mock_secrets.py`: Provides fake API keys for testing

These mocks create files in the `test_output/` directory for verification of the expected behavior.

## License

Proprietary

## Contributors

[Your Name/Organization] 