"""
Generate PDF lambda function.

This function converts the response from the Gemini API (markdown format)
into a professionally formatted PDF document for HRIM Wellness Centre.
"""

import json
import os
import logging
import sys
import io
import re
from datetime import datetime
import markdown
import xhtml2pdf.pisa as pisa
from typing import Tuple, Dict, Any, Optional, Callable

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def format_ai_response(response_md: str) -> str:
    """
    Format the AI response to ensure consistent structure that matches the HRIM Wellness Centre format.
    
    Args:
        response_md: The raw markdown response from the AI
        
    Returns:
        Formatted markdown response
    """
    # Replace common section headers to match the HRIM format
    formatted_response = response_md
    
    # Format the meal plan section header if it exists
    if "meal plan" in formatted_response.lower() and not "7-day diet & wellness plan" in formatted_response.lower():
        formatted_response = formatted_response.replace("# Meal Plan", "## 7-Day Diet & Wellness Plan")
        formatted_response = formatted_response.replace("## Meal Plan", "## 7-Day Diet & Wellness Plan")
    
    # Format the activity plan section header if it exists
    if "activity plan" in formatted_response.lower() and not "4-week wellness & activity plan" in formatted_response.lower():
        formatted_response = formatted_response.replace("# Activity Plan", "## 4-Week Wellness & Activity Plan (Gujarat)")
        formatted_response = formatted_response.replace("## Activity Plan", "## 4-Week Wellness & Activity Plan (Gujarat)")
    
    # Format grocery list header if it exists
    if "grocery" in formatted_response.lower() and not "grocery list" in formatted_response.lower():
        formatted_response = formatted_response.replace("# Grocery", "## Grocery List")
        formatted_response = formatted_response.replace("## Grocery", "## Grocery List")
    
    # Format do's and don'ts header if it exists
    if "do" in formatted_response.lower() and "don't" in formatted_response.lower() and not "do's and don'ts" in formatted_response.lower():
        formatted_response = formatted_response.replace("# Do's and Don'ts", "## Do's and Don'ts")
        formatted_response = formatted_response.replace("# Do's & Don'ts", "## Do's and Don'ts")
        formatted_response = formatted_response.replace("## Do's & Don'ts", "## Do's and Don'ts")
    
    # Format work-life balance section header if it exists
    if "work-life balance" in formatted_response.lower() or "work life balance" in formatted_response.lower():
        formatted_response = formatted_response.replace("# Work-Life Balance", "## Work-Life Balance Tips for Stress Management")
        formatted_response = formatted_response.replace("## Work-Life Balance", "## Work-Life Balance Tips for Stress Management")
        formatted_response = formatted_response.replace("# Work Life Balance", "## Work-Life Balance Tips for Stress Management")
        formatted_response = formatted_response.replace("## Work Life Balance", "## Work-Life Balance Tips for Stress Management")
    
    # Format summary header if it exists
    if "summary" in formatted_response.lower() and not "summary advice for follow-up" in formatted_response.lower():
        formatted_response = formatted_response.replace("# Summary", "## Summary Advice for Follow-Up")
        formatted_response = formatted_response.replace("## Summary", "## Summary Advice for Follow-Up")
    
    return formatted_response

def format_table_headers(html_content: str) -> str:
    """
    Format table headers with proper styling.
    
    Args:
        html_content: HTML content with tables
        
    Returns:
        HTML with properly styled table headers
    """
    # Replace default markdown table headers with properly styled ones
    # This makes table headers bold and centered
    html_content = html_content.replace('<th>', '<th style="background-color:#f2f2f2; text-align:center; font-weight:bold;">')
    return html_content

def format_wellness_plan(response_md: str, client_data: Dict[str, Any]) -> str:
    """
    Format the AI-generated content to match the HRIM Wellness Centre style.
    
    Args:
        response_md: The markdown response from the AI
        client_data: Client data dictionary
        
    Returns:
        Formatted markdown string
    """
    # Format the AI response to match the expected structure
    formatted_ai_response = format_ai_response(response_md)
    
    # Extract client name
    client_name = client_data.get('Full Name', 'Client')
    
    # Create headers based on screenshot format
    header = f"# HRIM Wellness Centre\n\n"
    
    # Client summary section
    client_summary = "## Diet & Wellness Plan\n\n"
    client_summary += "### Client Summary\n\n"
    client_summary += "#### Personal Details\n\n"
    
    # Add personal details based on client data
    # Format as bullet points to match screenshot
    client_summary += f"* **Name**: {client_data.get('Full Name', '')}\n"
    
    # Calculate age if DOB is provided
    dob = client_data.get('DOB', '')
    age = ''
    if dob:
        try:
            birth_date = datetime.strptime(dob, '%Y-%m-%d')
            today = datetime.now()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            age = f"{age} (Born: {dob})"
        except Exception as e:
            logger.warning(f"Error calculating age: {str(e)}")
            age = dob
    
    client_summary += f"* **Age**: {age}\n"
    client_summary += f"* **Gender**: {client_data.get('Gender', '')}\n"
    client_summary += f"* **Occupation**: {client_data.get('Occupation', '')}\n"
    
    # Add height and weight
    height = client_data.get('Height (in cm)', '')
    client_summary += f"* **Height**: {height} cm\n"
    
    weight = client_data.get('Current Weight (in kg)', '')
    client_summary += f"* **Weight**: {weight} kg\n"
    
    # Add health concerns section
    client_summary += "\n### Health Concerns\n\n"
    
    # Format primary health goals
    health_goals = client_data.get('Primary Health Goals', '')
    client_summary += f"* **Primary Health Goal**: {health_goals}\n"
    
    # Add medical conditions
    medical_conditions = client_data.get('If yes, please specify medical conditions.', 'No existing medical conditions reported')
    client_summary += f"* **Current Symptoms/Diagnosis**: {medical_conditions}\n"
    
    # Add medications
    medications = client_data.get('If yes, please specify medications', 'None')
    client_summary += f"* **Medications**: {medications}\n"
    
    # Add stress level
    stress_level = client_data.get('Stress Level', 'Moderate')
    client_summary += f"* **Stress Levels**: {stress_level}\n"
    
    # Add allergies
    allergies = client_data.get('If yes, Please specify allergies.', 'None reported')
    client_summary += f"* **Allergies**: {allergies}\n"
    
    # Add dietary habits section
    client_summary += "\n### Dietary Habits\n\n"
    
    # Add dietary preference
    diet_pref = client_data.get('Dietary Preference', '')
    client_summary += f"* **Dietary Preference**: {diet_pref}"
    if 'Gujarat' in client_data.get('State', ''):
        client_summary += " (assumed based on Gujarat's cultural context, as not explicitly stated)\n"
    else:
        client_summary += "\n"
    
    # Add meals per day
    meals_per_day = client_data.get('Meals per Day', '')
    client_summary += f"* **Meals Per Day**: {meals_per_day}\n"
    
    # Add snacking habits
    snacking = client_data.get('Snacking Habit', '')
    client_summary += f"* **Snacking Habit**: {snacking}\n"
    
    # Add water intake
    water = client_data.get('Water Intake Per Day (in Liters)', '')
    client_summary += f"* **Water Intake**: {water} liters/day\n"
    
    # Add caffeine intake
    caffeine = client_data.get('Consumption of Caffeine (Tea/Coffee) Cups Per Day', '')
    client_summary += f"* **Caffeine Intake**: {caffeine} cups/day (tea/coffee)\n"
    
    # Add eating out frequency
    eating_out = client_data.get('Frequency of Eating Out', '')
    client_summary += f"* **Frequency of Eating Out**: {eating_out}\n"
    
    # Add activity and lifestyle section
    client_summary += "\n### Activity & Lifestyle\n\n"
    
    # Add physical activity
    activity = client_data.get('Physical Activity Level', '')
    exercise = client_data.get('Exercise Routine (if any)', '')
    client_summary += f"* **Physical Activity**: {activity} ({exercise})\n"
    
    # Add sleep patterns
    sleep_hours = client_data.get('Average Hours of Sleep', '')
    wake_time = client_data.get('Wake-Up Time', '')
    sleep_time = client_data.get('Sleep Time', '')
    client_summary += f"* **Sleep**: {sleep_hours} hours (Wakeup: {wake_time}, Sleep: {sleep_time})\n"
    
    # Add screen time
    screen_time = client_data.get('Screen Time per Day (in Hours)', '')
    client_summary += f"* **Screen Time**: {screen_time} hours/day\n"
    
    # Add hobbies
    hobbies = client_data.get('Hobbies and Leisure Activities (Describe)', '')
    client_summary += f"* **Hobbies**: {hobbies}\n"
    
    # Add section divider
    divider = "\n---\n\n"
    
    # Add "Other Inputs" section as seen in page 2 of screenshots
    other_inputs = "## Other Inputs\n\n"
    
    # Add wellness goals
    other_inputs += f"* **Wellness Goals**: Weight loss\n"
    
    # Add emotional state 
    emotional_state = client_data.get('How often do you feel stressed?', 'Sometimes stressed')
    other_inputs += f"* **Emotional State**: {emotional_state}\n"
    
    # Add relaxation techniques
    relaxation = client_data.get('If yes, Specify relaxation techniques.', 'None reported')
    other_inputs += f"* **Relaxation Techniques**: {relaxation}\n"
    
    # Add menstrual health if female
    if client_data.get('Gender', '').lower() == 'female':
        other_inputs += "* **Menstrual Health**: Not specified (assumed regular based on age)\n"
    
    # Add cravings 
    other_inputs += "* **Cravings**: Not specified\n"
    
    # Add another divider
    other_inputs += "\n---\n\n"
    
    # Add nutritional goals section as seen in screenshots
    nutritional_goals = "## Nutritional Goals\n\n"
    
    # Calculate target weight if available
    current_weight = client_data.get('Current Weight (in kg)', '')
    target_weight = client_data.get('Target Weight (if any)', '')
    
    if current_weight and target_weight:
        try:
            weight_diff = abs(float(current_weight) - float(target_weight))
            nutritional_goals += f"* **Calorie Target**: ~1500-1600 kcal/day (to support gradual weight loss of ~0.5 kg/week)\n"
        except:
            nutritional_goals += f"* **Calorie Target**: ~1500-1600 kcal/day\n"
    else:
        nutritional_goals += f"* **Calorie Target**: ~1500-1600 kcal/day\n"
    
    # Add macronutrient breakdown
    nutritional_goals += "* **Macronutrient Breakdown**:\n"
    nutritional_goals += "  * Protein: 20% (~75-80 g)\n"
    nutritional_goals += "  * Fat: 25% (~40-45 g)\n"
    nutritional_goals += "  * Carbohydrates: 55% (~200-220 g)\n"
    nutritional_goals += "  * Fiber: 25-30 g/day\n"
    
    # Add focus
    nutritional_goals += "* **Focus**: High-fiber, moderate-protein vegetarian meals using Gujarat-specific ingredients, promoting satiety and mindful eating (75% full).\n"
    
    # Add another divider
    nutritional_goals += "\n---\n\n"
    
    # Combine all sections with the AI response
    # We'll replace any duplicate headers the AI might generate
    formatted_response = header + client_summary + divider + other_inputs + nutritional_goals + formatted_ai_response
    
    return formatted_response

def markdown_to_html(markdown_text: str, client_name: str) -> str:
    """
    Convert markdown text to HTML with additional styling.
    
    Args:
        markdown_text: The markdown text to convert
        client_name: Client name for title
        
    Returns:
        HTML string
    """
    # Convert markdown to HTML using a simple extension set
    # Avoid complex extensions that might cause issues with PDF conversion
    html_body = markdown.markdown(markdown_text, extensions=['tables'])
    
    # Apply additional formatting to tables
    html_body = format_table_headers(html_body)
    
    # Get current date for the header
    current_date = datetime.now().strftime("%d %B, %Y")
    
    # Create a styled HTML document with minimal features
    # Avoid complex CSS that might cause rendering issues
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>HRIM Wellness Centre - Diet & Wellness Plan</title>
        <style>
            @page {{
                size: letter;
                margin: 2cm;
            }}
            body {{
                font-family: serif;
                line-height: 1.5;
                margin: 0;
                padding: 0;
                color: #000;
                font-size: 11pt;
            }}
            .header {{
                text-align: center;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px solid #000;
            }}
            .header h1 {{
                font-size: 18pt;
                margin-bottom: 5px;
                font-weight: bold;
            }}
            .header p {{
                font-size: 10pt;
                margin: 2px 0;
            }}
            h1 {{
                font-size: 16pt;
                margin-top: 20px;
                margin-bottom: 10px;
                font-weight: bold;
                text-align: center;
            }}
            h2 {{
                font-size: 14pt;
                margin-top: 15px;
                margin-bottom: 10px;
                font-weight: bold;
            }}
            h3 {{
                font-size: 12pt;
                margin-top: 10px;
                margin-bottom: 5px;
                font-weight: bold;
            }}
            h4 {{
                font-size: 11pt;
                margin-top: 8px;
                margin-bottom: 5px;
                font-weight: bold;
            }}
            p {{
                margin-bottom: 10px;
                font-size: 11pt;
            }}
            ul, ol {{
                margin-top: 5px;
                margin-bottom: 10px;
            }}
            li {{
                margin-bottom: 5px;
                font-size: 11pt;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
                font-size: 10pt;
            }}
            tr {{
                page-break-inside: avoid;
            }}
            th {{
                background-color: #f2f2f2;
                border: 1px solid #000;
                padding: 5px;
                text-align: center;
                font-weight: bold;
                font-size: 10pt;
            }}
            td {{
                border: 1px solid #000;
                padding: 5px;
                text-align: left;
                font-size: 10pt;
            }}
            strong {{
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                font-size: 9pt;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>HRIM Wellness Centre</h1>
            <p>503, Takshshila Apartment, Dayalaji Ashram Marg, Majura Gate, Surat - 395001, Gujarat, India</p>
            <p>Phone: +91 94279 81235 | Email: hrimwellness@gmail.com | Web: www.hrimwellness.in</p>
            <p>Date: {current_date}</p>
        </div>
        
        <div class="content">
            {html_body}
        </div>
        
        <div class="footer">
            Page 1
        </div>
    </body>
    </html>
    """
    
    return html

def generate_pdf_from_html(html: str) -> Tuple[bytes, io.BytesIO]:
    """
    Generate a PDF from HTML content.
    
    Args:
        html: The HTML content to convert
        
    Returns:
        Tuple containing PDF bytes and BytesIO object
    """
    # Create a new BytesIO object
    pdf_data = io.BytesIO()
    
    try:
        # Define a simple link callback that returns None to avoid NotImplementedType error
        def link_callback(uri, rel):
            return None
        
        # Use CreatePDF with minimal options to avoid errors
        result = pisa.CreatePDF(
            src=html,
            dest=pdf_data,
            encoding='UTF-8',
            link_callback=link_callback
        )
        
        if result.err:
            logger.error(f"Error converting HTML to PDF: {result.err}")
            raise Exception(f"PDF generation failed: {result.err}")
        
        # Get PDF bytes and reset BytesIO position
        pdf_data.seek(0)
        pdf_bytes = pdf_data.getvalue()
        pdf_data.seek(0)
        
        return pdf_bytes, pdf_data
    
    except Exception as e:
        logger.error(f"Exception in PDF generation: {str(e)}", exc_info=True)
        
        # Create a simple fallback PDF with error message
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Error Report</title>
        </head>
        <body>
            <h1>Error Generating PDF</h1>
            <p>There was an error generating the PDF document. Please contact support.</p>
            <p>Error details: {str(e)}</p>
        </body>
        </html>
        """
        
        # Reset BytesIO object
        pdf_data = io.BytesIO()
        
        # Try again with minimal HTML
        pisa.CreatePDF(
            src=fallback_html,
            dest=pdf_data,
            encoding='UTF-8'
        )
        
        pdf_data.seek(0)
        pdf_bytes = pdf_data.getvalue()
        pdf_data.seek(0)
        
        return pdf_bytes, pdf_data

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict containing job_id, response, and client_data
        context: Lambda context
        
    Returns:
        Dict containing job ID, PDF key, and status
    """
    try:
        # Parse the event
        if 'body' in event:
            # If coming from API Gateway
            body = json.loads(event['body'])
            job_id = body.get('job_id')
            response_md = body.get('response')
            client_data = body.get('client_data')
        else:
            # If coming from direct Lambda invocation
            job_id = event.get('job_id')
            response_md = event.get('response')
            client_data = event.get('client_data')
        
        logger.info(f"Generating PDF for job: {job_id}")
        
        if not job_id or not response_md or not client_data:
            logger.error("Missing required parameters: job_id, response, or client_data")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Update job status
        utils.update_job_status(job_id, utils.JobStatus.GENERATING_PDF)
        
        # Get client name for PDF
        client_name = client_data.get('Full Name', 'Client')
        
        # Format the wellness plan
        formatted_response = format_wellness_plan(response_md, client_data)
        
        # Convert formatted response to HTML
        html = markdown_to_html(formatted_response, client_name)
        
        # Generate PDF
        pdf_bytes, pdf_data = generate_pdf_from_html(html)
        
        # Create a unique filename for the PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{client_name.replace(' ', '_')}_wellness_plan_{timestamp}.pdf"
        pdf_key = f"jobs/{job_id}/{pdf_filename}"
        
        # Store the PDF in S3
        utils.upload_binary_to_s3(
            utils.OUTPUT_BUCKET,
            pdf_key,
            pdf_bytes,
            'application/pdf'
        )
        
        logger.info(f"PDF generated and stored for job: {job_id}, key: {pdf_key}")
        
        # Prepare result for next step
        result = {
            'job_id': job_id,
            'pdf_key': pdf_key,
            'pdf_filename': pdf_filename,
            'client_data': client_data,
            'status': utils.JobStatus.UPLOADING_PDF
        }
        
        # Update job status to indicate we're moving to upload PDF
        utils.update_job_status(job_id, utils.JobStatus.UPLOADING_PDF)
        
        logger.info(f"Job {job_id} proceeding to upload_pdf")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error in generate_pdf: {str(e)}", exc_info=True)
        
        # Update job status to failed if we have a job ID
        if 'job_id' in locals() and job_id:
            error_message = f"PDF generation error: {str(e)}"
            utils.update_job_status(job_id, utils.JobStatus.FAILED, error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 