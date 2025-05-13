# HRIM: Health & Wellness Report Implementation Manager

An automated system for generating personalized wellness plans using AWS serverless architecture and Google's Gemini API.

## Overview

HRIM automates the process of generating personalized wellness and diet plans for clients based on data collected via Google Forms. The system:

1. Retrieves client data from Google Forms (stored in AWS S3) 
2. Processes it using the Google Gemini API
3. Generates a comprehensive wellness plan in PDF format
4. Stores the generated PDF back on S3
5. Delivers it to the client via email

The entire process takes approximately 15 seconds from form submission to email delivery.

## Technical Architecture

- **Backend**: AWS Lambda functions written in Python
- **Workflow Orchestration**: AWS Step Functions
- **Data Storage**: AWS S3 for raw data and generated PDFs, DynamoDB for job tracking
- **AI**: Google Gemini API for generating personalized wellness content
- **Communication**: AWS SES for email delivery
- **Form Integration**: Google Apps Script for Google Form integration
- **API Gateway**: REST endpoint to receive Google Form submissions

## Standard Prompt Template

HRIM uses a standardized prompt template stored as `prompt.txt` in the S3 bucket. This approach offers several advantages:

1. **Consistency**: All wellness plans use the same prompt structure, ensuring consistent quality and format
2. **Easy Updates**: The prompt can be modified without changing code by simply updating the template file in S3
3. **Direct Data Flow**: The system sends both the prompt template and client data directly to Gemini AI

The workflow for prompt handling:

1. The standard prompt is stored at `templates/prompt.txt` in the input S3 bucket
2. When processing a form submission, the system:
   - Retrieves the standard prompt template from S3
   - Sends both the prompt and the client data to Gemini API
   - The Gemini AI uses the prompt as instructions and the client data as input

To modify the prompt template:
```bash
# Update the prompt template in S3
./upload_prompt_template.sh [your-bucket-name]
```

To test the prompt implementation:
```bash
# Test the prompt with sample client data
./test_prompt_implementation.py
```

## Repository Structure

```
HRIM/
├── doc/                # Project documentation
│   └── google_form_integration.md  # Google Form integration documentation
├── src/                # Source code
│   ├── google_form_integration/    # Google Apps Script for Form integration
│   └── lambda/         # Lambda functions for each processing step
│       ├── trigger_processor/      # Handles S3 events and starts the workflow
│       ├── fetch_data/             # Retrieves client data from S3
│       ├── format_prompt/          # Prepares data for the Gemini API
│       ├── call_gemini/            # Calls the Gemini API and handles response
│       ├── generate_pdf/           # Creates PDF from the Gemini response
│       ├── upload_pdf/             # Uploads the PDF to S3
│       ├── send_email/             # Sends the PDF via email
│       ├── form_submission/        # Handles Google Form submissions
│       └── complete_job/           # Updates job status and handling completion
├── terraform/          # Infrastructure as code (Terraform)
├── test-data/          # Sample data for testing
├── test_hrim.py        # Test script for local testing
├── test_form_submission.py  # Test script for form submission
├── test_instant_delivery.py # Test script for instant delivery performance
├── test_prompt_implementation.py # Test script for prompt template usage
├── upload_prompt_template.sh # Script to upload prompt template to S3
├── requirements.txt    # Python dependencies
├── deploy.sh           # Deployment script
└── README.md           # This file
```

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure AWS credentials using the AWS CLI:
   ```
   aws configure
   ```
4. Obtain a Google Gemini API key from [Google AI Studio](https://ai.google.dev/)
5. Export required environment variables:
   ```
   export GEMINI_API_KEY=your-gemini-api-key
   export SENDER_EMAIL=your-verified-email@example.com
   ```
   
   Note: For SES, you need to verify your email in the AWS SES console.

## Local Testing

You can test the system locally without deploying to AWS by using the provided test scripts:

### Basic Testing

```bash
python test_hrim.py [optional-email-address]
```

This script:
1. Loads the sample client data from `test-data/sample-form-submission.json`
2. Runs through the entire workflow by calling each Lambda function locally
3. Generates a PDF in the `test_output/pdfs` directory
4. Optionally sends the PDF via email if an address is provided (requires AWS SES setup)

### Testing Instant Email Delivery

```bash
python test_instant_delivery.py [your-email@example.com]
```

This script:
1. Tests the complete flow from form submission to email delivery
2. Measures the time it takes to generate and deliver the wellness plan
3. Reports detailed timing for each step of the process
4. Verifies that the email is delivered quickly (typically within 15 seconds)

## Deployment

To deploy the system to AWS:

1. Make sure you have AWS credentials configured
2. Ensure you have Terraform installed
3. Update the `terraform/variables.tf` file with your configuration
4. Run the deployment script:
   ```
   ./deploy.sh
   ```

The script will:
1. Package all Lambda functions into ZIP files
2. Create a Lambda layer with dependencies
3. Initialize and apply the Terraform configuration

## Google Form Integration

HRIM integrates with Google Forms to collect client data and automatically generate wellness plans. For setup:

1. Deploy the AWS infrastructure with `terraform apply`
2. Note the API Gateway URL that Terraform outputs
3. Set up Google Apps Script with your Google Form
4. Configure the script to send form data to your API Gateway

The integration allows clients to receive their wellness plans via email within approximately 15 seconds of form submission.

For detailed instructions, see [Google Form Integration Guide](doc/google_form_integration.md).

You can test the form submission process with:

```bash
python test_form_submission.py [your-api-gateway-url]
```

## Instant Email Delivery

The system is optimized for fast delivery:

1. **No Delays**: All processing steps happen immediately with no artificial delays
2. **Performance Monitoring**: Each step logs its execution time for analysis
3. **Optimized Lambda Functions**: Functions are designed for fast execution
4. **Enhanced Error Handling**: Improved error handling to prevent delays

Key optimizations include:
- Removing delays in the `complete_job` Lambda function
- Enhanced error handling in `send_email` Lambda function
- Optimized workflow with minimal wait times
- Fast PDF generation and email processing

## Using Gemini API Instead of OpenAI

This implementation uses Google's Gemini API instead of OpenAI's GPT models. Key differences:

1. Authentication is handled using an API key from Google AI Studio
2. The response format and API structure are different
3. Prompt formatting is optimized for Gemini's capabilities

## Customization

1. **Client Data Format**: The system expects client data in a specific format. See `test-data/sample-form-submission.json` for an example.
2. **Prompt Template**: The prompt for Gemini is defined in `src/lambda/format_prompt/lambda_function.py`. You can customize it to change the style or content of the wellness plan.
3. **PDF Styling**: The PDF styling is defined in `src/lambda/generate_pdf/lambda_function.py`. Customize the HTML template to change the appearance of the PDF.
4. **Email Template**: The email content is defined in `src/lambda/send_email/lambda_function.py`. Modify the HTML and text templates as needed.
5. **Google Form**: The form submission handling is in `src/lambda/form_submission/lambda_function.py`. Modify the field mapping if you change your form fields.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Proprietary

## Contributors

[Your Name/Organization] 