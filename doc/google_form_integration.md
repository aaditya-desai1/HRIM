# Google Form Integration with HRIM

This document explains how to integrate your Google Form with the HRIM (Health & Wellness Report Implementation Manager) system to automatically generate wellness plans when a client submits the form.

## Overview

The integration follows this workflow:

1. Client submits a form through your Google Form
2. Google Apps Script attached to the form sends the data to AWS API Gateway
3. API Gateway triggers a Lambda function
4. Lambda stores the form data in S3
5. S3 event triggers the HRIM workflow
6. HRIM generates the wellness plan and delivers it to the client

## Current Form Structure

The current Google Form (as of May 2023) is available at:
https://docs.google.com/forms/d/e/1FAIpQLScRfePeKf3gkXVrykQej6RHOBN42Paz7mT1_-pB1jl92Lu0kQ/viewform

The form collects the following information:
- **Basic Information**: Email, Full Name, Phone Number, Date of Birth, Gender, Height, Weight, City, Occupation
- **Medical Information**: Medical Conditions, Allergies or Sensitivities, Current Medications
- **Diet Preferences**: Dietary Preference, Meals per Day, Usual Meal Times, Cuisine Preference, Foods You Enjoy, Foods You Dislike
- **Lifestyle**: Activity Level, Current Exercise Routine, Sleep Pattern, Stress Level, Daily Water Intake
- **Goals and Constraints**: Health Goals, Weight Management Goal, Energy Level Concerns, Food Budget, Available Cooking Time, Household Size, Previous Diet Plans
- **Additional Information**: Free text field for any other relevant details

## Setup Instructions

### 1. Deploy AWS Infrastructure

First, deploy the AWS infrastructure that will handle form submissions:

```bash
# Make sure you have the latest code
git pull

# Deploy infrastructure using Terraform
cd terraform
terraform init
terraform apply
```

This will create:
- API Gateway endpoint to receive form data
- Lambda function to process form data
- Necessary IAM permissions
- S3 bucket configuration

After deployment, Terraform will output the API Gateway endpoint URL. Note this URL as you'll need it in the next step.

### 2. Set Up Google Apps Script

1. Open your Google Form at: https://docs.google.com/forms/d/e/1FAIpQLScRfePeKf3gkXVrykQej6RHOBN42Paz7mT1_-pB1jl92Lu0kQ/viewform
2. Click on the three dots (⋮) in the top right corner and select "Script editor"
3. In the script editor, delete any existing code
4. Copy and paste the code from `src/google_form_integration/GoogleFormToS3.js`
5. Replace the `API_ENDPOINT` constant with your API Gateway URL:
   ```javascript
   const API_ENDPOINT = "https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/v1/form-submission";
   ```
6. Save the script (File > Save)
7. Set up a trigger to run the script when the form is submitted:
   - Click on "Triggers" (clock icon) in the left sidebar
   - Click "Add Trigger"
   - Configure the trigger:
     - Choose which function to run: `onFormSubmit`
     - Choose which deployment should run: `Head`
     - Select event source: `From form`
     - Select event type: `On form submit`
   - Click "Save"
8. You'll be prompted to authorize the script. Follow the prompts to grant permission.

### 3. Test the Integration

You can test the integration using the provided test script:

```bash
# Install required dependencies
pip install requests

# Test the updated form submission locally
python test_updated_form.py

# Run the test script with your API Gateway URL
python test_form_submission.py https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/v1/form-submission

# To run in mock mode without sending actual requests
python test_form_submission.py --mock
```

You can also test by submitting a real form response through your Google Form.

### 4. Verify Data Flow

After submitting a form, you can verify that the data is flowing through the system:

1. Check AWS CloudWatch logs for the `hrim-form-submission` Lambda function
2. Verify that the form data is stored in the S3 bucket in the `incoming/` folder
3. Check that the HRIM workflow is triggered and processing the form data
4. Verify that the client receives the wellness plan via email

## Troubleshooting

### Google Apps Script Issues

- **Authorization Failed**: Make sure you've granted the necessary permissions to the script
- **Script Error**: Check the script logs in the Apps Script editor (View > Logs)
- **Quota Limits**: Google Apps Script has usage quotas. Check if you're hitting any limits.

### AWS Integration Issues

- **API Gateway 4xx Errors**: Check your request format and CORS configuration
- **Lambda Errors**: Check CloudWatch logs for the Lambda function
- **S3 Permissions**: Ensure the Lambda function has permissions to write to S3

### Form Data Mapping Issues

If there are issues with the format of the data:

1. Submit a test form manually
2. Check the AWS CloudWatch logs to see how the data is being received
3. Adjust the field mappings in the `standardize_form_data` function in the Lambda code

## Custom Field Mapping

If you modify your Google Form, you'll need to update the field mapping in the Lambda function. Edit the `standardize_form_data` function in `src/lambda/form_submission/lambda_function.py` to match your form fields.

Current field mapping (as of May 2023):
```python
field_mapping = {
    'Full Name': 'Full Name',
    'Email': 'Email',
    'Phone Number': 'Phone Number',
    'Date of Birth': 'Date of Birth',
    'Gender': 'Gender',
    'Height': 'Height',
    'Weight': 'Weight',
    'City': 'City',
    'Occupation': 'Occupation',
    'Medical Conditions': 'Medical Conditions',
    'Allergies or Sensitivities': 'Allergies or Sensitivities',
    'Current Medications': 'Current Medications',
    'Dietary Preference': 'Dietary Preference',
    'Meals per Day': 'Meals per Day',
    'Usual Meal Times': 'Usual Meal Times',
    'Cuisine Preference': 'Cuisine Preference',
    'Foods You Enjoy': 'Foods You Enjoy',
    'Foods You Dislike': 'Foods You Dislike',
    'Activity Level': 'Activity Level',
    'Current Exercise Routine': 'Current Exercise Routine',
    'Sleep Pattern': 'Sleep Pattern',
    'Stress Level': 'Stress Level',
    'Daily Water Intake': 'Daily Water Intake',
    'Health Goals': 'Wellness Goals',
    'Weight Management Goal': 'Weight Management Goal',
    'Energy Level Concerns': 'Energy Level Concerns',
    'Food Budget': 'Food Budget',
    'Available Cooking Time': 'Available Cooking Time',
    'Household Size': 'Household Size',
    'Previous Diet Plans': 'Previous Diet Plans',
    'Additional Information': 'Additional Information'
}
```

## Security Considerations

- The API Gateway endpoint is publicly accessible. Consider adding authentication if needed.
- Google Apps Script stores your form data. Review Google's privacy policies.
- The integration transmits client health data. Ensure compliance with relevant regulations (HIPAA, GDPR, etc.).