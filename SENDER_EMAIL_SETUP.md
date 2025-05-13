# Setting Up Sender Email in HRIM

This document explains how to configure the sender email address for the HRIM (Health & Wellness Report Implementation Manager) system.

## Overview

HRIM sends personalized wellness plans via email using Amazon SES. The system needs a verified sender email address to work properly.

> **IMPORTANT UPDATE**: The system now uses `desaiaditya2710@gmail.com` as the sender email address by default for all emails. This is hardcoded in the Lambda functions to avoid "Message Rejected" errors. The configuration methods below can be used for additional flexibility but are not required for basic functionality.

## Available Methods

There are several ways to set the sender email (though the default will work in most cases):

### 1. Use the `update_sender_email.sh` Script

This script updates both your local environment and deployed Lambda functions:

```bash
# Make the script executable if needed
chmod +x update_sender_email.sh

# Run the script with default settings (uses desaiaditya2710@gmail.com)
./update_sender_email.sh

# Update only local environment, not Lambda functions
./update_sender_email.sh --local-only

# Or specify a different email address (not recommended unless verified in SES)
./update_sender_email.sh --sender-email your-email@example.com

# Specify a different AWS region
./update_sender_email.sh --region us-west-2
```

### 2. Set Environment Variable for Local Testing

For local testing:

```bash
# Set the environment variable for the current shell session
export SENDER_EMAIL=desaiaditya2710@gmail.com

# Run your tests
python test_hrim.py
python test_instant_delivery.py
```

### 3. Update Terraform Variables

For a permanent configuration that will be applied on deployment:

1. Create or edit the `terraform/terraform.tfvars` file:

```bash
# Create the file if it doesn't exist
touch terraform/terraform.tfvars
```

2. Add the sender email variable:

```
sender_email = "desaiaditya2710@gmail.com"
```

3. Apply the Terraform configuration:

```bash
cd terraform
terraform apply
```

## Testing Email Sending

To verify that your sender email is working:

### Basic SES Test

```bash
# Run the SES simulator test
python test_ses_simulator.py
```

### Test the Email Lambda Function

```bash
# Test the complete send_email Lambda function
python test_email_sender.py
```

### Test the Complete Flow with Simulator

```bash
# Test the complete flow with the SES simulator
python monitor_form_submission.py --use-simulator
```

## SES Simulator Mode

When testing with Amazon SES, you can use special simulator addresses:

- `success@simulator.amazonses.com` - Simulates successful delivery
- `bounce@simulator.amazonses.com` - Simulates a bounced email
- `complaint@simulator.amazonses.com` - Simulates a complaint

The system always uses `desaiaditya2710@gmail.com` as the sender email address, which works seamlessly with the simulator addresses.

## SES Sandbox Mode

New AWS accounts start in "SES Sandbox" mode, which has these restrictions:

1. You can only send TO email addresses that are verified in SES
2. You can only send FROM email addresses that are verified in SES
3. You have a limit of 200 emails per 24-hour period

To get out of sandbox mode, you need to request production access through the AWS SES console.

## Troubleshooting

If you encounter email sending issues:

1. Verify that `desaiaditya2710@gmail.com` is verified in Amazon SES in your account
2. Check if your account is in sandbox mode
3. If in sandbox mode, verify recipient email addresses as well
4. Check AWS CloudWatch logs for error messages

If you encounter a "MessageRejected" error, it typically means that the sender email address isn't verified in SES. The system should now always use `desaiaditya2710@gmail.com` which avoids this issue. 