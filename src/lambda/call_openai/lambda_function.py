import json
import os
import sys
import logging
import boto3
import time
import openai
from botocore.exceptions import ClientError

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_manager = boto3.client('secretsmanager')

# Constants
OPENAI_API_KEY_SECRET_NAME = os.environ.get('OPENAI_API_KEY_SECRET_NAME', 'HRIM/OpenAI/ApiKey')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
# Set to true to use local mock response file instead of calling OpenAI API
USE_LOCAL_MOCK = os.environ.get('USE_LOCAL_MOCK', 'false').lower() == 'true'
LOCAL_MOCK_FILE = os.environ.get('LOCAL_MOCK_FILE', 'mock_responses/wellness_plan.txt')

def lambda_handler(event, context):
    """
    Lambda function to call the OpenAI GPT-4o API with the formatted prompt.
    
    Args:
        event (dict): Input event containing job_id and formatted_prompt
        context (LambdaContext): Lambda context
        
    Returns:
        dict: GPT-4o API response and job ID
    """
    logger.info(f"Received event for OpenAI API call")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        formatted_prompt = event.get('formatted_prompt')
        
        if not all([job_id, formatted_prompt]):
            error_message = "Missing required parameters in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Update job status
        utils.update_job_status(job_id, 'CALLING_OPENAI')
        
        # Check if we should use local mock file
        if USE_LOCAL_MOCK:
            logger.info(f"Using local mock response from {LOCAL_MOCK_FILE}")
            gpt_response = get_local_mock_response(LOCAL_MOCK_FILE)
            logger.info("Successfully loaded mock OpenAI response")
        else:
            # Get OpenAI API key from Secrets Manager
            api_key = get_openai_api_key()
            if not api_key:
                error_message = "Failed to retrieve OpenAI API key"
                utils.handle_error(job_id, error_message)
                return {
                    'statusCode': 500,
                    'error': error_message
                }
            
            # Configure OpenAI client
            openai.api_key = api_key
            
            # Call OpenAI API with retry logic
            gpt_response = call_openai_with_retry(formatted_prompt)
            
            logger.info(f"Successfully received OpenAI API response for job {job_id}")
        
        # Update job status
        utils.update_job_status(job_id, 'OPENAI_RESPONSE_RECEIVED')
        
        # Return the GPT response and job ID for the next step
        return {
            'job_id': job_id,
            'gpt_response': gpt_response
        }
    
    except Exception as e:
        error_message = f"Error in call_openai: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def get_local_mock_response(file_path):
    """
    Get a mock response from a local file instead of calling OpenAI API.
    
    Args:
        file_path (str): Path to the mock response file
        
    Returns:
        str: Content of the mock response file
        
    Raises:
        Exception: If file cannot be read
    """
    try:
        # Support both absolute and relative paths
        if not os.path.isabs(file_path):
            # Try to find the file in several common locations
            potential_paths = [
                file_path,
                os.path.join(os.path.dirname(__file__), file_path),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_path),
                os.path.join('src', 'lambda', 'mocks', 'mock_responses', os.path.basename(file_path)),
            ]
            
            for path in potential_paths:
                if os.path.exists(path):
                    file_path = path
                    break
            else:
                raise FileNotFoundError(f"Could not find mock response file in any of: {potential_paths}")
        
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading mock response file: {str(e)}")
        # Return a minimal default response if file cannot be read
        return """# Four-Week Meal Plan

## Week 1 Meal Plan:
- This is a mock wellness plan.
- The actual file could not be loaded.

## DOs:
- DO include protein-rich foods
- DO drink at least 8 glasses of water

## DON'Ts:
- DON'T skip meals
- DON'T consume caffeine after 2 PM

## Summary & Follow-up
This is a mock wellness plan for testing purposes only.
"""

def get_openai_api_key():
    """
    Get OpenAI API key from AWS Secrets Manager.
    
    Returns:
        str: OpenAI API key
    """
    try:
        response = secrets_manager.get_secret_value(
            SecretId=OPENAI_API_KEY_SECRET_NAME
        )
        secret = json.loads(response['SecretString'])
        return secret.get('api_key')
    except ClientError as e:
        logger.error(f"Error retrieving OpenAI API key: {str(e)}")
        return None

def call_openai_with_retry(formatted_prompt):
    """
    Call OpenAI API with retry logic for transient errors.
    
    Args:
        formatted_prompt (dict): Formatted prompt with system and user messages
        
    Returns:
        str: GPT-4o response text
        
    Raises:
        Exception: If API call fails after all retries
    """
    retries = 0
    while retries < MAX_RETRIES:
        try:
            logger.info(f"Calling OpenAI API (attempt {retries + 1}/{MAX_RETRIES})")
            
            response = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": formatted_prompt["system"]},
                    {"role": "user", "content": formatted_prompt["user"]}
                ],
                temperature=0.7,
                max_tokens=4000,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract the response text
            return response.choices[0].message.content
            
        except (openai.APIError, openai.APIConnectionError, openai.RateLimitError) as e:
            retries += 1
            if retries < MAX_RETRIES:
                logger.warning(f"OpenAI API error: {str(e)}. Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS * (2 ** (retries - 1)))  # Exponential backoff
            else:
                logger.error(f"OpenAI API error after {MAX_RETRIES} retries: {str(e)}")
                raise Exception(f"Failed to call OpenAI API after {MAX_RETRIES} retries: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI API: {str(e)}")
            raise