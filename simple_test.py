#!/usr/bin/env python3
"""
Simplified test script for the HRIM project.

This script provides a basic end-to-end test of the workflow without requiring
any external APIs or services.
"""

import json
import os
import sys
import logging
import uuid
from datetime import datetime
import xhtml2pdf.pisa as pisa
import io
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simple_test')

def create_output_directories():
    """Create directories for test outputs."""
    dirs = [
        'test_output',
        'test_output/pdfs',
        'test_output/mock_emails',
        'test_output/mock_whatsapp',
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def load_test_data():
    """Load test data from the test-data directory."""
    test_data_file = os.path.join('test-data', 'sample-form-submission.json')
    
    if not os.path.exists(test_data_file):
        logger.error(f"Test data file not found: {test_data_file}")
        return None
        
    with open(test_data_file, 'r') as f:
        return json.load(f)

def generate_mock_wellness_plan(client_data):
    """Generate a mock wellness plan based on client data."""
    name = client_data.get('Full Name', 'Client')
    age = client_data.get('Age', '30')
    goals = client_data.get('Health Goals', 'weight management, better sleep')
    
    # Create a simple wellness plan template
    wellness_plan = f"""
# Personalized Wellness Plan for {name}

## Overview
This personalized wellness plan is designed for a {age}-year-old individual 
with the following health goals: {goals}.

## Four-Week Meal Plan

### Week 1 Meal Plan:
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
This personalized wellness plan addresses the specified health goals through balanced nutrition and lifestyle modifications.
"""
    return wellness_plan

def format_prompt(client_data):
    """Format a prompt for the wellness plan generation."""
    name = client_data.get('Full Name', 'Unknown')
    age = client_data.get('Age', 'Unknown')
    height = client_data.get('Height', 'Unknown')
    weight = client_data.get('Weight', 'Unknown')
    goals = client_data.get('Health Goals', 'Unknown')
    
    prompt = f"""
Please create a comprehensive wellness plan for the following client:

Name: {name}
Age: {age}
Height: {height}
Weight: {weight}
Health Goals: {goals}

The wellness plan should include:
1. A four-week meal plan
2. Daily routine recommendations
3. DOs and DON'Ts
4. Summary and follow-up recommendations
"""
    return prompt

def simulate_openai_response(prompt):
    """Simulate an OpenAI API response."""
    # Extract client info from the prompt
    name_start = prompt.find("Name: ") + 6
    name_end = prompt.find("\n", name_start)
    name = prompt[name_start:name_end]
    
    goals_start = prompt.find("Health Goals: ") + 14
    goals_end = prompt.find("\n", goals_start)
    goals = prompt[goals_start:goals_end]
    
    # Generate a mock wellness plan
    wellness_plan = f"""
# Personalized Wellness Plan for {name}

## Overview
This personalized wellness plan is designed to help you achieve your health goals: {goals}.

## Four-Week Meal Plan

### Week 1 Meal Plan:
- **Breakfast**: Masala Oats with Almonds and Fresh Fruits
- **Lunch**: Rajma Chawal with Jeera Raita
- **Dinner**: Roti with Palak Tofu Curry
- **Snack 1**: Chickpea Chaat
- **Snack 2**: Apple with Peanut Butter

### Week 2 Meal Plan:
- **Breakfast**: Vegetable Poha with Yogurt
- **Lunch**: Vegetable Khichdi with Cucumber Raita
- **Dinner**: Mixed Vegetable Curry with Millet Roti
- **Snack 1**: Mixed Nuts and Dried Fruits
- **Snack 2**: Vegetable Soup

## Daily Routine Recommendations:
- Morning: Start your day with a glass of warm water with lemon
- Noon: Take a 15-minute walk after lunch
- Evening: Practice 20 minutes of yoga or meditation
- Night: Avoid screens 1 hour before bedtime

## DOs:
- DO include protein-rich foods like lentils, chickpeas, and tofu in every meal
- DO drink at least 8 glasses of water throughout the day
- DO practice mindful eating by chewing slowly and avoiding distractions

## DON'Ts:
- DON'T skip meals, especially breakfast
- DON'T consume caffeine after 2 PM as it may affect sleep quality
- DON'T eat heavy meals within 2 hours of bedtime

## Summary & Follow-up
This personalized wellness plan addresses your specific health goals through balanced nutrition and lifestyle modifications. Follow-up in 4 weeks is recommended to assess progress and make adjustments.
"""
    return wellness_plan

def generate_pdf(wellness_plan, client_name):
    """Generate a PDF from the wellness plan."""
    # Convert markdown to HTML (simple conversion)
    html = "<html><head><style>"
    html += "body { font-family: Arial, sans-serif; margin: 40px; }"
    html += "h1 { color: #2c3e50; }"
    html += "h2 { color: #3498db; margin-top: 20px; }"
    html += "h3 { color: #2980b9; }"
    html += "ul { margin-bottom: 15px; }"
    html += "li { margin-bottom: 5px; }"
    html += "</style></head><body>"
    
    # Simple markdown to HTML conversion
    for line in wellness_plan.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            html += f"<h1>{line[2:]}</h1>"
        elif line.startswith('## '):
            html += f"<h2>{line[3:]}</h2>"
        elif line.startswith('### '):
            html += f"<h3>{line[4:]}</h3>"
        elif line.startswith('- '):
            if not html.endswith('</ul>') and not html.endswith('<ul>'):
                html += "<ul>"
            html += f"<li>{line[2:]}</li>"
        elif line == '' and html.endswith('</li>'):
            html += "</ul>"
        elif line:
            html += f"<p>{line}</p>"
    
    html += "</body></html>"
    
    # Create PDF
    pdf_data = io.BytesIO()
    pisa.CreatePDF(html, dest=pdf_data)
    pdf_data.seek(0)
    
    # Save PDF to file for verification
    filename = f"{client_name.replace(' ', '_')}_wellness_plan.pdf"
    pdf_path = os.path.join('test_output', 'pdfs', filename)
    with open(pdf_path, 'wb') as f:
        f.write(pdf_data.read())
    
    pdf_data.seek(0)
    return pdf_data.read(), pdf_path

def mock_send_email(client_data, pdf_path):
    """Mock sending an email with the PDF attachment."""
    client_name = client_data.get('Full Name', 'Client')
    client_email = client_data.get('Email', 'unknown@example.com')
    
    # Create a mock email record
    email_content = f"""
To: {client_email}
From: wellness@example.com
Subject: Your Personalized Wellness Plan
Attachments: {pdf_path}

Hello {client_name},

Your personalized wellness plan is attached to this email.

Thank you for choosing our wellness planning service!
"""
    
    # Save the mock email for verification
    email_file = os.path.join('test_output', 'mock_emails', f"{client_name.replace(' ', '_')}_email.txt")
    with open(email_file, 'w') as f:
        f.write(email_content)
    
    logger.info(f"Mock email sent to {client_email}")
    return email_file

def mock_send_whatsapp(client_data, pdf_path):
    """Mock sending a WhatsApp message with the PDF attachment."""
    client_name = client_data.get('Full Name', 'Client')
    client_whatsapp = client_data.get('WhatsApp Contact Number', '+1234567890')
    
    # Create a mock WhatsApp message record
    whatsapp_content = f"""
To: {client_whatsapp}
From: Wellness Center
Message: Hello {client_name}, your personalized wellness plan is ready! Please check your email.
Attachments: {pdf_path}
"""
    
    # Save the mock WhatsApp message for verification
    whatsapp_file = os.path.join('test_output', 'mock_whatsapp', f"{client_name.replace(' ', '_')}_whatsapp.txt")
    with open(whatsapp_file, 'w') as f:
        f.write(whatsapp_content)
    
    logger.info(f"Mock WhatsApp message sent to {client_whatsapp}")
    return whatsapp_file

def run_simple_test():
    """Run a simple end-to-end test of the workflow."""
    start_time = datetime.now()
    logger.info("Starting simple end-to-end test")
    
    # Create output directories
    create_output_directories()
    
    # Load test data
    client_data = load_test_data()
    if not client_data:
        logger.error("Failed to load test data")
        return False
    
    client_name = client_data.get('Full Name', 'Unknown Client')
    logger.info(f"Loaded test data for client: {client_name}")
    
    # Step 1: Format prompt
    logger.info("Step 1: Formatting prompt for wellness plan")
    prompt = format_prompt(client_data)
    
    # Step 2: Simulate OpenAI call
    logger.info("Step 2: Simulating OpenAI API call")
    wellness_plan = simulate_openai_response(prompt)
    
    # Step 3: Generate PDF
    logger.info("Step 3: Generating PDF from wellness plan")
    pdf_data, pdf_path = generate_pdf(wellness_plan, client_name)
    logger.info(f"PDF generated and saved to {pdf_path}")
    
    # Step 4: Mock email delivery
    logger.info("Step 4: Simulating email delivery")
    email_file = mock_send_email(client_data, pdf_path)
    logger.info(f"Email details saved to {email_file}")
    
    # Step 5: Mock WhatsApp delivery
    logger.info("Step 5: Simulating WhatsApp delivery")
    whatsapp_file = mock_send_whatsapp(client_data, pdf_path)
    logger.info(f"WhatsApp details saved to {whatsapp_file}")
    
    # Calculate processing time
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    logger.info(f"Test completed successfully in {processing_time:.2f} seconds")
    logger.info(f"All outputs are available in the test_output directory")
    
    return True

if __name__ == "__main__":
    success = run_simple_test()
    sys.exit(0 if success else 1) 