#!/usr/bin/env python3
"""
Script to verify the sender email in Amazon SES.

This script checks if desaiaditya2710@gmail.com is verified in AWS SES,
and if not, sends a verification email.
"""

import boto3
import argparse
import time
import sys

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Verify sender email in Amazon SES')
    parser.add_argument('--email', default='desaiaditya2710@gmail.com', 
                        help='Email address to verify (default: desaiaditya2710@gmail.com)')
    parser.add_argument('--region', default='us-east-1', 
                        help='AWS region (default: us-east-1)')
    parser.add_argument('--check-only', action='store_true',
                        help='Only check verification status, do not send verification email')
    return parser.parse_args()

def check_email_verification(ses_client, email):
    """Check if the email is verified in SES."""
    try:
        response = ses_client.list_verified_email_addresses()
        verified_emails = response.get('VerifiedEmailAddresses', [])
        
        if email in verified_emails:
            print(f"✅ Email {email} is already verified in SES.")
            return True
        else:
            print(f"❌ Email {email} is NOT verified in SES.")
            return False
    except Exception as e:
        print(f"Error checking email verification: {str(e)}")
        return False

def send_verification_email(ses_client, email):
    """Send a verification email to the specified address."""
    try:
        ses_client.verify_email_identity(EmailAddress=email)
        print(f"✅ Verification email sent to {email}.")
        print("Please check your inbox and click the verification link to complete the process.")
        return True
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False

def check_ses_account_status(ses_client):
    """Check if the SES account is in sandbox mode."""
    try:
        quota = ses_client.get_send_quota()
        max_send_rate = quota.get('MaxSendRate')
        
        # If max send rate is 1 or less, we're likely in sandbox mode
        is_sandbox = max_send_rate <= 1
        
        if is_sandbox:
            print("⚠️ Your AWS account is in SES SANDBOX mode.")
            print("   Both sender and recipient email addresses must be verified.")
        else:
            print("🚀 Your AWS account is in SES PRODUCTION mode.")
            print("   Only sender email addresses need to be verified.")
        
        return is_sandbox
    except Exception as e:
        print(f"Error checking SES account status: {str(e)}")
        return True  # Assume sandbox mode to be safe

def main():
    """Main function."""
    args = parse_arguments()
    
    print("=== Amazon SES Email Verification ===")
    print(f"Email: {args.email}")
    print(f"Region: {args.region}")
    print()
    
    # Create SES client
    ses_client = boto3.client('ses', region_name=args.region)
    
    # Check SES account status
    is_sandbox = check_ses_account_status(ses_client)
    print()
    
    # Check if email is verified
    is_verified = check_email_verification(ses_client, args.email)
    
    if not is_verified and not args.check_only:
        print("\nSending verification email...")
        if send_verification_email(ses_client, args.email):
            print("\nPlease follow these steps to complete verification:")
            print("1. Check the inbox of", args.email)
            print("2. Look for an email from Amazon SES")
            print("3. Click the verification link in that email")
            print("4. Wait a few minutes for the verification to propagate")
            print("5. Run this script again with --check-only to confirm verification")
    
    if not is_verified and args.check_only:
        print("\n⚠️ Email is not verified. Run without --check-only to send verification email.")
        sys.exit(1)
    
    print("\n=== Verification Check Complete ===")
    
    # Return success only if verified
    sys.exit(0 if is_verified else 1)

if __name__ == "__main__":
    main() 