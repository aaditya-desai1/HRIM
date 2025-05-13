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

## License

Proprietary

## Contributors

[Your Name/Organization] 