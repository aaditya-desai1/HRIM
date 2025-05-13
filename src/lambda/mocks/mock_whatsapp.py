import json
import os
import logging
import requests
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MockWhatsAppResponse:
    """Mock response from WhatsApp API."""
    
    @staticmethod
    def json():
        """Return a mock successful response JSON."""
        return {
            "messaging_product": "whatsapp",
            "contacts": [
                {
                    "input": "mock-phone-number",
                    "wa_id": "mock-whatsapp-id"
                }
            ],
            "messages": [
                {
                    "id": f"wamid.mock-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                }
            ]
        }
    
    @property
    def status_code(self):
        """Return mock status code."""
        return 200
    
    @property
    def text(self):
        """Return mock response text."""
        return json.dumps(self.json())

def mock_whatsapp_post(*args, **kwargs):
    """
    Mock implementation of requests.post for WhatsApp API.
    
    Args:
        args: Positional arguments passed to requests.post
        kwargs: Keyword arguments passed to requests.post
        
    Returns:
        MockWhatsAppResponse: A mock response object
    """
    # Extract API endpoint and headers
    url = args[0] if args else kwargs.get('url', 'https://mock-whatsapp-api.example.com')
    headers = kwargs.get('headers', {})
    json_data = kwargs.get('json', {})
    
    # Log the WhatsApp API call
    logger.info(f"MOCK WHATSAPP API CALL: {url}")
    logger.info(f"Headers: {json.dumps(headers)}")
    logger.info(f"Payload: {json.dumps(json_data)}")
    
    # Save mock WhatsApp message to file for testing/verification
    mock_whatsapp_dir = os.path.join(os.path.dirname(__file__), "mock_whatsapp")
    os.makedirs(mock_whatsapp_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"whatsapp_{timestamp}.json"
    file_path = os.path.join(mock_whatsapp_dir, filename)
    
    with open(file_path, "w") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "headers": headers,
            "payload": json_data,
            "mock_response": MockWhatsAppResponse.json()
        }, indent=2))
    
    logger.info(f"Mock WhatsApp message saved to {file_path}")
    
    # Return mock response
    return MockWhatsAppResponse()

# Store original post function to restore if needed
original_post = requests.post

def patch_requests():
    """Patch the requests.post function with our mock implementation."""
    requests.post = mock_whatsapp_post
    logger.info("Patched requests.post for WhatsApp API mocking")

def unpatch_requests():
    """Restore the original requests.post function."""
    requests.post = original_post
    logger.info("Restored original requests.post function") 