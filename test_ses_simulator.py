#!/usr/bin/env python3
"""
Test script to verify SES email sending with the simulator.

This script tests sending emails using the Amazon SES simulator addresses
with desaiaditya2710@gmail.com as the sender.
"""

import boto3
import os
import argparse
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test SES simulator email sending.')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--sender', type=str, default='desaiaditya2710@gmail.com', 
                        help='Sender email address (must be verified in SES)')
    parser.add_argument('--simulator', type=str, default='success@simulator.amazonses.com',
                        choices=['success@simulator.amazonses.com',
                                'bounce@simulator.amazonses.com',
                                'complaint@simulator.amazonses.com'],
                        help='SES simulator address to use')
    return parser.parse_args()

def verify_sender_email(ses_client, sender_email):
    """Verify that the sender email is verified in SES."""
    try:
        response = ses_client.list_verified_email_addresses()
        verified_emails = response.get('VerifiedEmailAddresses', [])
        
        if sender_email not in verified_emails:
            print(f"WARNING: {sender_email} is not verified in SES.")
            print("Would you like to send a verification email? (y/n)")
            choice = input().lower()
            
            if choice == 'y':
                ses_client.verify_email_identity(EmailAddress=sender_email)
                print(f"Verification email sent to {sender_email}.")
                print("Please check your inbox and click the verification link.")
                print("Then run this script again.")
                return False
            else:
                print("Continuing without verification. This may cause errors.")
        else:
            print(f"✅ Sender email {sender_email} is verified in SES.")
            return True
    except Exception as e:
        print(f"Error checking email verification: {str(e)}")
        return False

def check_ses_account_status(ses_client):
    """Check if the SES account is in sandbox mode."""
    try:
        quota = ses_client.get_send_quota()
        max_send_rate = quota.get('MaxSendRate')
        
        # If max send rate is 1 or less, we're likely in sandbox mode
        is_sandbox = max_send_rate <= 1
        
        print(f"SES account status: {'SANDBOX' if is_sandbox else 'PRODUCTION'}")
        return is_sandbox
    except Exception as e:
        print(f"Error checking SES account status: {str(e)}")
        return True  # Assume sandbox mode to be safe

def send_test_email(ses_client, sender_email, recipient_email):
    """Send a test email using SES."""
    try:
        # Create a multipart email
        msg = MIMEMultipart()
        msg['Subject'] = 'HRIM Test Email - SES Simulator'
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # Add text body
        text = f"""
Hello,

This is a test email sent from {sender_email} to the SES simulator address {recipient_email}.
This test confirms that the HRIM system is correctly configured to send emails.

Regards,
HRIM Test System
        """
        
        text_part = MIMEText(text, 'plain')
        msg.attach(text_part)
        
        # Convert the message to a string
        raw_message = msg.as_string().encode('utf-8')
        
        # Send the email
        print(f"Sending test email from {sender_email} to {recipient_email}...")
        response = ses_client.send_raw_email(
            Source=sender_email,
            Destinations=[recipient_email],
            RawMessage={'Data': raw_message}
        )
        
        message_id = response.get('MessageId')
        print(f"✅ Email sent successfully! Message ID: {message_id}")
        return True, message_id
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False, None

def main():
    """Main function."""
    args = parse_arguments()
    
    # Set the sender email as an environment variable
    os.environ['SENDER_EMAIL'] = args.sender
    
    print("=== HRIM SES Simulator Test ===")
    print(f"Sender: {args.sender}")
    print(f"Recipient: {args.simulator}")
    print(f"Region: {args.region}")
    print()
    
    # Create SES client
    ses_client = boto3.client('ses', region_name=args.region)
    
    # Check if sender is verified
    if not verify_sender_email(ses_client, args.sender):
        print("Please verify the sender email and try again.")
        return
    
    # Check SES account status
    is_sandbox = check_ses_account_status(ses_client)
    print()
    
    # Send test email
    success, message_id = send_test_email(ses_client, args.sender, args.simulator)
    
    if success:
        print()
        print("Test email sent successfully to the SES simulator.")
        print(f"Using {args.sender} as the sender email address.")
        print()
        print("NOTE: The SES simulator doesn't actually deliver emails,")
        print("      but it confirms that your AWS configuration is correct.")
        
        if args.simulator == 'success@simulator.amazonses.com':
            print()
            print("To check if emails are being correctly processed by HRIM,")
            print("run the monitor_form_submission.py script with the --use-simulator flag:")
            print()
            print("python monitor_form_submission.py --use-simulator")
    else:
        print()
        print("Failed to send test email. Please check the error message above.")
        
    print()
    print("=== Test Complete ===")

if __name__ == "__main__":
    main() 