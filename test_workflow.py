#!/usr/bin/env python3
"""
Simplified test script for the HRIM workflow.

This script simulates the wellness plan generation workflow
without requiring the actual Lambda functions to be implemented.
"""

import json
import os
import sys
import logging
import uuid
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_workflow')

def load_test_data():
    """Load test data from the test-data directory."""
    test_data_file = os.path.join('test-data', 'sample-form-submission.json')
    
    if not os.path.exists(test_data_file):
        logger.error(f"Test data file not found: {test_data_file}")
        return None
        
    with open(test_data_file, 'r') as f:
        return json.load(f)

def create_output_directories():
    """Create directories for test outputs."""
    dirs = [
        'test_output',
        'test_output/pdfs',
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def simulate_wellness_plan():
    """Simulate generating a wellness plan."""
    # Create a sample wellness plan (abbreviated version)
    return """
# Four-Week Meal Plan

## Week 1 Meal Plan:

### Monday
- **Breakfast**: Masala Oats with Almonds and Fresh Fruits
- **Lunch**: Rajma Chawal with Jeera Raita
- **Dinner**: Roti with Palak Tofu Curry
- **Snack 1**: Chickpea Chaat
- **Snack 2**: Apple with Peanut Butter

## DOs:
- DO include protein-rich foods like lentils, chickpeas, and tofu in every meal
- DO drink at least 8 glasses of water throughout the day
- DO practice mindful eating by chewing slowly and avoiding distractions

## DON'Ts:
- DON'T skip meals, especially breakfast
- DON'T consume caffeine after 2 PM as it may affect sleep quality
- DON'T eat heavy meals within 2 hours of bedtime

## Summary & Follow-up

This personalized wellness plan addresses weight gain, boosting immunity, reducing stress, and improving sleep quality through balanced nutrition and lifestyle modifications.
"""

def generate_sample_pdf(wellness_plan, output_path):
    """Generate a simple text file as a placeholder for a PDF."""
    # In a real implementation, this would create a PDF
    # For testing, we'll just create a text file
    with open(output_path, 'w') as f:
        f.write(wellness_plan)
    logger.info(f"Generated sample output file: {output_path}")

def simulate_workflow():
    """Simulate the entire wellness plan generation workflow."""
    logger.info("Starting test workflow simulation")
    
    # Create output directories
    create_output_directories()
    
    # Load test data
    client_data = load_test_data()
    if not client_data:
        logger.error("Failed to load test data")
        return False
    
    logger.info(f"Loaded test data for client: {client_data.get('Full Name', 'Unknown')}")
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    # Simulate workflow steps
    logger.info(f"Step 1: Triggered workflow for job {job_id}")
    
    logger.info("Step 2: Fetching and validating client data")
    client_name = client_data.get('Full Name', 'Unknown Client')
    client_email = client_data.get('Email', 'unknown@example.com')
    client_whatsapp = client_data.get('WhatsApp Contact Number', '+1234567890')
    
    logger.info("Step 3: Formatting prompt for wellness plan generation")
    # In a real implementation, this would create a structured prompt
    
    logger.info("Step 4: Generating wellness plan content")
    wellness_plan = simulate_wellness_plan()
    
    logger.info("Step 5: Creating PDF document")
    pdf_filename = f"{client_name.replace(' ', '_')}_wellness_plan_{job_id[:8]}.txt"
    pdf_path = os.path.join('test_output', 'pdfs', pdf_filename)
    generate_sample_pdf(wellness_plan, pdf_path)
    
    logger.info("Step 6: Simulating delivery")
    logger.info(f"  - Email delivery to: {client_email}")
    logger.info(f"  - WhatsApp delivery to: {client_whatsapp}")
    
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    logger.info(f"Workflow completed in {processing_time:.2f} seconds")
    logger.info(f"Output file available at: {pdf_path}")
    
    return True

if __name__ == "__main__":
    success = simulate_workflow()
    sys.exit(0 if success else 1) 