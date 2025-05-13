import json
import os
import sys
import logging
import re
from io import BytesIO
from xhtml2pdf import pisa
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to generate a PDF from the OpenAI GPT-4o response.
    
    Args:
        event (dict): Input event containing job_id and gpt_response
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Generated PDF data and job ID
    """
    logger.info(f"Received event for PDF generation")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        gpt_response = event.get('gpt_response')
        
        if not all([job_id, gpt_response]):
            error_message = "Missing required parameters in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Update job status
        utils.update_job_status(job_id, 'GENERATING_PDF')
        
        # Parse the GPT response to extract sections
        parsed_content = parse_gpt_response(gpt_response)
        
        # Generate PDF from parsed content
        pdf_data = generate_pdf_from_content(parsed_content)
        
        logger.info(f"Successfully generated PDF for job {job_id}")
        
        # Update job status
        utils.update_job_status(job_id, 'PDF_GENERATED')
        
        # Return the PDF data and job ID for the next step
        return {
            'job_id': job_id,
            'pdf_data': pdf_data.decode('latin1')  # Encode binary data for JSON
        }
    
    except Exception as e:
        error_message = f"Error in generate_pdf: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def parse_gpt_response(gpt_response):
    """
    Parse the GPT response text to extract the different sections.
    
    Args:
        gpt_response (str): Raw GPT-4o text response
        
    Returns:
        dict: Parsed content with sections
    """
    # Initialize with default empty sections
    parsed_content = {
        'meal_plans': {
            'week1': [],
            'week2': [],
            'week3': [],
            'week4': []
        },
        'routine_charts': {
            'week1': [],
            'week2': [],
            'week3': [],
            'week4': []
        },
        'grocery_lists': {
            'week1': [],
            'week2': [],
            'week3': [],
            'week4': []
        },
        'dos_donts': {
            'dos': [],
            'donts': []
        },
        'stress_tips': {
            'week1': [],
            'week2': [],
            'week3': [],
            'week4': []
        },
        'summary': ""
    }
    
    # Extract sections using pattern matching
    # This is a simplified parser - a more robust approach would be needed for production
    
    # Extract meal plans
    meal_plan_pattern = r"(?:Week \d+[^\n]*Meal Plan:?)(.*?)(?:(?:Week \d+|Weekly Daily Routine|Weekly Grocery|DOs & DON'Ts))"
    meal_plan_matches = re.findall(meal_plan_pattern, gpt_response, re.DOTALL)
    
    for i, match in enumerate(meal_plan_matches[:4]):  # Up to 4 weeks
        week_key = f'week{i+1}'
        parsed_content['meal_plans'][week_key] = match.strip()
    
    # Extract routine charts
    routine_pattern = r"(?:Week \d+[^\n]*Daily Routine:?)(.*?)(?:(?:Week \d+|Weekly Grocery|DOs & DON'Ts))"
    routine_matches = re.findall(routine_pattern, gpt_response, re.DOTALL)
    
    for i, match in enumerate(routine_matches[:4]):  # Up to 4 weeks
        week_key = f'week{i+1}'
        parsed_content['routine_charts'][week_key] = match.strip()
    
    # Extract grocery lists
    grocery_pattern = r"(?:Week \d+[^\n]*Grocery List:?)(.*?)(?:(?:Week \d+|DOs & DON'Ts|Stress & Balance))"
    grocery_matches = re.findall(grocery_pattern, gpt_response, re.DOTALL)
    
    for i, match in enumerate(grocery_matches[:4]):  # Up to 4 weeks
        week_key = f'week{i+1}'
        parsed_content['grocery_lists'][week_key] = match.strip()
    
    # Extract DOs and DON'Ts
    dos_pattern = r"(?:DOs:)(.*?)(?:DON'Ts:)"
    dos_match = re.search(dos_pattern, gpt_response, re.DOTALL)
    if dos_match:
        dos_text = dos_match.group(1).strip()
        parsed_content['dos_donts']['dos'] = [item.strip() for item in dos_text.split('\n') if item.strip()]
    
    donts_pattern = r"(?:DON'Ts:)(.*?)(?:Stress & Balance|Summary)"
    donts_match = re.search(donts_pattern, gpt_response, re.DOTALL)
    if donts_match:
        donts_text = donts_match.group(1).strip()
        parsed_content['dos_donts']['donts'] = [item.strip() for item in donts_text.split('\n') if item.strip()]
    
    # Extract stress tips
    stress_pattern = r"(?:Week \d+[^\n]*Stress & Balance Tips:?)(.*?)(?:(?:Week \d+|Summary))"
    stress_matches = re.findall(stress_pattern, gpt_response, re.DOTALL)
    
    for i, match in enumerate(stress_matches[:4]):  # Up to 4 weeks
        week_key = f'week{i+1}'
        parsed_content['stress_tips'][week_key] = match.strip()
    
    # Extract summary
    summary_pattern = r"(?:Summary & Follow-up:?)(.*?)$"
    summary_match = re.search(summary_pattern, gpt_response, re.DOTALL)
    if summary_match:
        parsed_content['summary'] = summary_match.group(1).strip()
    
    return parsed_content

def generate_pdf_from_content(parsed_content):
    """
    Generate a PDF from the parsed content.
    
    Args:
        parsed_content (dict): Parsed content with sections
        
    Returns:
        bytes: PDF file as bytes
    """
    # Create PDF buffer
    buffer = BytesIO()
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Custom styles
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    subheader_style = ParagraphStyle(
        'SubHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.darkblue
    )
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch/2,
        leftMargin=inch/2,
        topMargin=inch/2,
        bottomMargin=inch/2
    )
    
    # Build content
    content = []
    
    # Add title
    content.append(Paragraph("Personalized Wellness Plan", header_style))
    content.append(Spacer(1, 0.25*inch))
    
    # Add meal plans
    content.append(Paragraph("Four-Week Meal Plan", header_style))
    for week_num in range(1, 5):
        week_key = f'week{week_num}'
        content.append(Paragraph(f"Week {week_num} Meal Plan", subheader_style))
        content.append(Paragraph(parsed_content['meal_plans'][week_key], normal_style))
        content.append(Spacer(1, 0.25*inch))
    
    # Add routine charts
    content.append(Paragraph("Weekly Daily Routine Charts", header_style))
    for week_num in range(1, 5):
        week_key = f'week{week_num}'
        content.append(Paragraph(f"Week {week_num} Daily Routine", subheader_style))
        content.append(Paragraph(parsed_content['routine_charts'][week_key], normal_style))
        content.append(Spacer(1, 0.25*inch))
    
    # Add grocery lists
    content.append(Paragraph("Weekly Grocery Lists", header_style))
    for week_num in range(1, 5):
        week_key = f'week{week_num}'
        content.append(Paragraph(f"Week {week_num} Grocery List", subheader_style))
        content.append(Paragraph(parsed_content['grocery_lists'][week_key], normal_style))
        content.append(Spacer(1, 0.25*inch))
    
    # Add DOs and DON'Ts
    content.append(Paragraph("DOs & DON'Ts", header_style))
    
    content.append(Paragraph("DOs:", subheader_style))
    for do_item in parsed_content['dos_donts']['dos']:
        content.append(Paragraph(f"• {do_item}", normal_style))
    content.append(Spacer(1, 0.25*inch))
    
    content.append(Paragraph("DON'Ts:", subheader_style))
    for dont_item in parsed_content['dos_donts']['donts']:
        content.append(Paragraph(f"• {dont_item}", normal_style))
    content.append(Spacer(1, 0.25*inch))
    
    # Add stress tips
    content.append(Paragraph("Stress & Balance Tips", header_style))
    for week_num in range(1, 5):
        week_key = f'week{week_num}'
        content.append(Paragraph(f"Week {week_num} Stress & Balance Tips", subheader_style))
        content.append(Paragraph(parsed_content['stress_tips'][week_key], normal_style))
        content.append(Spacer(1, 0.25*inch))
    
    # Add summary
    content.append(Paragraph("Summary & Follow-up", header_style))
    content.append(Paragraph(parsed_content['summary'], normal_style))
    
    # Build the PDF
    doc.build(content)
    
    # Get the PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data 