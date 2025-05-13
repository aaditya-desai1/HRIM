import json
import os
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MockSES:
    """Mock implementation of AWS SES client."""
    
    @staticmethod
    def send_raw_email(Source, Destinations, RawMessage):
        """
        Simulate sending an email through AWS SES.
        
        Args:
            Source (str): Email sender address
            Destinations (list): List of recipient email addresses
            RawMessage (dict): Contains the raw email data
            
        Returns:
            dict: Mock response with MessageId
        """
        logger.info(f"MOCK EMAIL: From {Source} to {', '.join(Destinations)}")
        
        # Save mock email to file for testing/verification
        mock_email_dir = os.path.join(os.path.dirname(__file__), "mock_emails")
        os.makedirs(mock_email_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"email_{timestamp}.txt"
        file_path = os.path.join(mock_email_dir, filename)
        
        with open(file_path, "w") as f:
            f.write(f"From: {Source}\n")
            f.write(f"To: {', '.join(Destinations)}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Raw Message: {RawMessage['Data'][:1000]}...\n")  # First 1000 chars for brevity
        
        logger.info(f"Mock email saved to {file_path}")
        
        # Return a mock response similar to SES
        return {
            "MessageId": f"mock-message-{timestamp}"
        }
    
    @staticmethod
    def get_send_quota():
        """Mock implementation of get_send_quota."""
        return {
            "Max24HourSend": 1000.0,
            "MaxSendRate": 100.0,
            "SentLast24Hours": 0.0
        }

def get_mock_ses_client():
    """Return a mock SES client instance."""
    return MockSES 