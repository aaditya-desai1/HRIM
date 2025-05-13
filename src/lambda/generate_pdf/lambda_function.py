"""
Generate PDF lambda function.

This function converts the response from the Gemini API (markdown format)
into a professionally formatted PDF document.
"""

import json
import os
import logging
import sys
import io
from datetime import datetime
import markdown
import xhtml2pdf.pisa as pisa
from typing import Tuple, Dict, Any

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def markdown_to_html(markdown_text: str, client_name: str) -> str:
    """
    Convert markdown text to HTML with additional styling.
    
    Args:
        markdown_text: The markdown text to convert
        client_name: Client name for title
        
    Returns:
        HTML string
    """
    # Convert markdown to HTML
    html_body = markdown.markdown(markdown_text, extensions=['tables', 'nl2br'])
    
    # Create a styled HTML document
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Wellness Plan for {client_name}</title>
        <style>
            @page {{
                size: letter;
                margin: 2cm;
            }}
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.5;
                margin: 0;
                padding: 0;
                color: #333;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 1px solid #4CAF50;
                padding-bottom: 10px;
                color: #4CAF50;
            }}
            h1 {{
                color: #2E7D32;
                font-size: 28px;
                margin-top: 30px;
                margin-bottom: 15px;
            }}
            h2 {{
                color: #388E3C;
                font-size: 22px;
                margin-top: 25px;
                margin-bottom: 10px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            h3 {{
                color: #43A047;
                font-size: 18px;
                margin-top: 20px;
                margin-bottom: 10px;
            }}
            p {{
                margin-bottom: 10px;
            }}
            ul, ol {{
                margin-top: 5px;
                margin-bottom: 15px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            th {{
                background-color: #E8F5E9;
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #4CAF50;
                font-size: 12px;
                color: #777;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Personalized Wellness & Diet Plan</h1>
            <h2>Prepared for: {client_name}</h2>
            <p>Created on: {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        {html_body}
        
        <div class="footer">
            <p>This personalized plan was created based on your specific information and wellness goals.</p>
            <p>For questions or adjustments, please contact your wellness consultant.</p>
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
    pdf_data = io.BytesIO()
    
    # Convert HTML to PDF
    result = pisa.CreatePDF(
        src=html,
        dest=pdf_data,
        encoding='UTF-8'
    )
    
    if result.err:
        logger.error(f"Error converting HTML to PDF: {result.err}")
        raise Exception(f"PDF generation failed: {result.err}")
    
    # Get PDF bytes and reset BytesIO position
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
        
        # Convert markdown to HTML
        html = markdown_to_html(response_md, client_name)
        
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