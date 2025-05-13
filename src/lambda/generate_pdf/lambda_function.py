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
    
    # Determine diet type based on client data
    diet_pref = client_data.get('Dietary Preference', '').lower()
    meal_plan_type = "Meal"
    if 'vegan' in diet_pref:
        meal_plan_type = "Vegan"
    elif 'vegetarian' in diet_pref:
        meal_plan_type = "Vegetarian"
    elif 'non-veg' in diet_pref or 'non veg' in diet_pref:
        meal_plan_type = "Non-Vegetarian"
    elif 'egg' in diet_pref:
        meal_plan_type = "Egg-Vegetarian"
    
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
            age = f"{age}"
        except Exception as e:
            logger.warning(f"Error calculating age: {str(e)}")
            age = "35 (estimated)"
    else:
        age = "35 (estimated)"
    
    client_summary += f"* **Age**: {age}\n"
    client_summary += f"* **Gender**: {client_data.get('Gender', 'Not specified')}\n"
    
    # Set default occupation if missing
    occupation = client_data.get('Occupation', '')
    if not occupation:
        occupation = "Not specified"
    client_summary += f"* **Occupation**: {occupation}\n"
    
    # Add height and weight with defaults if missing
    height = client_data.get('Height (in cm)', '')
    if not height:
        height = client_data.get('Height', '')
    if not height:
        height = "170 (estimated)"
    else:
        # If height exists but doesn't have units, assume it's in cm
        height = f"{height} cm"
    client_summary += f"* **Height**: {height}\n"
    
    weight = client_data.get('Current Weight (in kg)', '')
    if not weight:
        weight = client_data.get('Weight', '')
    if not weight:
        weight = "70 (estimated)"
    else:
        # If weight exists but doesn't have units, assume it's in kg
        weight = f"{weight} kg"
    client_summary += f"* **Weight**: {weight}\n"
    
    # Add health concerns section
    client_summary += "\n### Health Concerns\n\n"
    
    # Format primary health goals with defaults if missing
    health_goals = client_data.get('Primary Health Goals', '')
    if not health_goals:
        health_goals = client_data.get('Wellness Goals', '')
    if not health_goals:
        health_goals = "Weight management and overall wellness"
    client_summary += f"* **Primary Health Goal**: {health_goals}\n"
    
    # Add medical conditions with defaults if missing
    medical_conditions = client_data.get('If yes, please specify medical conditions.', '')
    if not medical_conditions:
        medical_conditions = "No existing medical conditions reported"
    client_summary += f"* **Current Symptoms/Diagnosis**: {medical_conditions}\n"
    
    # Add medications with defaults if missing
    medications = client_data.get('If yes, please specify medications', '')
    if not medications:
        medications = "None"
    client_summary += f"* **Medications**: {medications}\n"
    
    # Add stress level with defaults if missing
    stress_level = client_data.get('Stress Level', '')
    if not stress_level:
        stress_level = "Moderate"
    client_summary += f"* **Stress Levels**: {stress_level}\n"
    
    # Add allergies with defaults if missing
    allergies = client_data.get('If yes, Please specify allergies.', '')
    if not allergies:
        allergies = "None reported"
    client_summary += f"* **Allergies**: {allergies}\n"
    
    # Add dietary habits section
    client_summary += "\n### Dietary Habits\n\n"
    
    # Add dietary preference with defaults if missing
    diet_pref = client_data.get('Dietary Preference', '')
    if not diet_pref:
        if 'Gujarat' in client_data.get('State', ''):
            diet_pref = "Vegetarian (assumed based on Gujarat's cultural context)"
        else:
            diet_pref = "Not specified"
    client_summary += f"* **Dietary Preference**: {diet_pref}\n"
    
    # Add meals per day with defaults if missing
    meals_per_day = client_data.get('Meals per Day', '')
    if not meals_per_day:
        meals_per_day = "3-4"
    client_summary += f"* **Meals Per Day**: {meals_per_day}\n"
    
    # Add snacking habits with defaults if missing
    snacking = client_data.get('Snacking Habit', '')
    if not snacking:
        snacking = "Occasional"
    client_summary += f"* **Snacking Habit**: {snacking}\n"
    
    # Add water intake with defaults if missing
    water = client_data.get('Water Intake Per Day (in Liters)', '')
    if not water:
        water = "2"
    client_summary += f"* **Water Intake**: {water} liters/day\n"
    
    # Add caffeine intake with defaults if missing
    caffeine = client_data.get('Consumption of Caffeine (Tea/Coffee) Cups Per Day', '')
    if not caffeine:
        caffeine = "2"
    client_summary += f"* **Caffeine Intake**: {caffeine} cups/day (tea/coffee)\n"
    
    # Add eating out frequency with defaults if missing
    eating_out = client_data.get('Frequency of Eating Out', '')
    if not eating_out:
        eating_out = "Weekly"
    client_summary += f"* **Frequency of Eating Out**: {eating_out}\n"
    
    # Add activity and lifestyle section
    client_summary += "\n### Activity & Lifestyle\n\n"
    
    # Add physical activity with defaults if missing
    activity = client_data.get('Physical Activity Level', '')
    exercise = client_data.get('Exercise Routine (if any)', '')
    if not activity:
        activity = "Moderate"
    if not exercise:
        exercise = "Regular walking"
    client_summary += f"* **Physical Activity**: {activity} ({exercise})\n"
    
    # Add sleep patterns with defaults if missing
    sleep_hours = client_data.get('Average Hours of Sleep', '')
    wake_time = client_data.get('Wake-Up Time', '')
    sleep_time = client_data.get('Sleep Time', '')
    if not sleep_hours:
        sleep_hours = "7"
    if not wake_time:
        wake_time = "6:30 AM"
    if not sleep_time:
        sleep_time = "11:30 PM"
    client_summary += f"* **Sleep**: {sleep_hours} hours (Wakeup: {wake_time}, Sleep: {sleep_time})\n"
    
    # Add screen time with defaults if missing
    screen_time = client_data.get('Screen Time per Day (in Hours)', '')
    if not screen_time:
        screen_time = "6-8"
    client_summary += f"* **Screen Time**: {screen_time} hours/day\n"
    
    # Add hobbies with defaults if missing
    hobbies = client_data.get('Hobbies and Leisure Activities (Describe)', '')
    if not hobbies:
        hobbies = "Reading, watching movies"
    client_summary += f"* **Hobbies**: {hobbies}\n"
    
    # Add section divider
    divider = "\n---\n\n"
    
    # Add "Other Inputs" section as seen in page 2 of screenshots
    other_inputs = "## Other Inputs\n\n"
    
    # Add wellness goals
    wellness_goals = client_data.get('Wellness Goals', '')
    if not wellness_goals:
        wellness_goals = client_data.get('Primary Health Goals', '')
    if not wellness_goals:
        wellness_goals = "Weight management and improved energy levels"
    other_inputs += f"* **Wellness Goals**: {wellness_goals}\n"
    
    # Add emotional state with defaults if missing 
    emotional_state = client_data.get('How often do you feel stressed?', '')
    if not emotional_state:
        emotional_state = "Sometimes stressed"
    other_inputs += f"* **Emotional State**: {emotional_state}\n"
    
    # Add relaxation techniques with defaults if missing
    relaxation = client_data.get('If yes, Specify relaxation techniques.', '')
    if not relaxation:
        relaxation = "None reported"
    other_inputs += f"* **Relaxation Techniques**: {relaxation}\n"
    
    # Add menstrual health if female
    if client_data.get('Gender', '').lower() == 'female':
        other_inputs += "* **Menstrual Health**: Not specified (assumed regular based on age)\n"
    
    # Add cravings with defaults if missing
    other_inputs += "* **Cravings**: Not specified\n"
    
    # Add another divider
    other_inputs += "\n---\n\n"
    
    # Add nutritional goals section as seen in screenshots
    nutritional_goals = "## Nutritional Goals\n\n"
    
    # Calculate target weight if available
    current_weight = client_data.get('Current Weight (in kg)', '')
    if not current_weight:
        current_weight = client_data.get('Weight', '')
        
    target_weight = client_data.get('Target Weight (if any)', '')
    if not target_weight:
        target_weight = client_data.get('Target Weight', '')
    
    if current_weight and target_weight:
        try:
            weight_diff = abs(float(current_weight) - float(target_weight))
            nutritional_goals += f"* **Calorie Target**: ~1500-1600 kcal/day (to support gradual weight loss of ~0.5 kg/week)\n"
        except:
            nutritional_goals += f"* **Calorie Target**: ~1800-2000 kcal/day\n"
    else:
        nutritional_goals += f"* **Calorie Target**: ~1800-2000 kcal/day\n"
    
    # Add macronutrient breakdown
    nutritional_goals += "* **Macronutrient Breakdown**:\n"
    nutritional_goals += "  * Protein: 20-25% (~75-80 g)\n"
    nutritional_goals += "  * Fat: 25-30% (~40-45 g)\n"
    nutritional_goals += "  * Carbohydrates: 45-55% (~200-220 g)\n"
    nutritional_goals += "  * Fiber: 25-30 g/day\n"
    
    # Add focus based on diet preference
    nutrition_focus = "balanced nutrition with proper portion control"
    if 'vegan' in diet_pref.lower():
        nutrition_focus = "high-fiber, plant-based proteins, and essential nutrients from vegan sources"
    elif 'vegetarian' in diet_pref.lower():
        nutrition_focus = "balanced vegetarian nutrition with adequate protein from dairy and plant sources"
    elif 'non-veg' in diet_pref.lower() or 'non veg' in diet_pref.lower():
        nutrition_focus = "balanced nutrition with lean protein sources and portion control"
    
    nutritional_goals += f"* **Focus**: {nutrition_focus}, promoting satiety and mindful eating (75% full).\n"
    
    # Add another divider
    nutritional_goals += "\n---\n\n"
    
    # Update meal plan title to match diet preference if needed
    if '4-WEEK VEGAN MEAL PLAN' in formatted_ai_response:
        formatted_ai_response = formatted_ai_response.replace('4-WEEK VEGAN MEAL PLAN', f'4-WEEK {meal_plan_type.upper()} MEAL PLAN')
    
    # Combine all sections with the AI response but remove the possible duplicate heading
    # Remove duplicate "HRIM Wellness Centre" if it exists in the AI response
    if formatted_ai_response.startswith("# HRIM Wellness Centre"):
        lines = formatted_ai_response.split('\n', 2)
        if len(lines) >= 3:
            formatted_ai_response = lines[2].lstrip()
    
    # Combine all sections
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
    
    # Remove the "EXTRACTED CLIENT INFORMATION" section
    if "EXTRACTED CLIENT INFORMATION" in html_body:
        parts = html_body.split("<h1>HRIM Wellness Centre</h1>", 1)
        if len(parts) > 1:
            before_header = parts[0]
            after_header = parts[1]
            
            # Remove duplicate header that appears right after the first one
            if "<h1>HRIM Wellness Centre</h1>" in after_header:
                after_header = after_header.replace("<h1>HRIM Wellness Centre</h1>", "", 1)
            
            # Remove the extracted client information section
            if "<h2>1) EXTRACTED CLIENT INFORMATION:" in after_header:
                section_parts = after_header.split("<h2>1) EXTRACTED CLIENT INFORMATION:", 1)
                if len(section_parts) > 1:
                    # Find the end of the section
                    end_parts = section_parts[1].split("<h2>", 1)
                    if len(end_parts) > 1:
                        # Reconstruct without the extracted section
                        after_header = section_parts[0] + "<h2>" + end_parts[1]
                    else:
                        # If no more h2, just use the part before the section
                        after_header = section_parts[0]
            
            # Reconstruct the HTML
            html_body = before_header + "<h1>HRIM Wellness Centre</h1>" + after_header
    
    # Remove duplicate HRIM Wellness Centre heading and client summary
    # First find the Diet & Wellness Plan heading
    if "<h2>Diet &amp; Wellness Plan</h2>" in html_body:
        # Check if there's a duplicate HRIM Wellness Centre heading before Diet & Wellness Plan
        diet_plan_parts = html_body.split("<h2>Diet &amp; Wellness Plan</h2>", 1)
        if len(diet_plan_parts) > 1:
            before_diet_plan = diet_plan_parts[0]
            after_diet_plan = diet_plan_parts[1]
            
            # Remove duplicate HRIM Wellness Centre heading if it exists between the first one and Diet & Wellness Plan
            wellness_center_matches = re.findall(r'<h1>HRIM Wellness Centre</h1>', before_diet_plan)
            if len(wellness_center_matches) > 1:
                # Keep only the first occurrence
                last_index = before_diet_plan.rindex('<h1>HRIM Wellness Centre</h1>')
                before_diet_plan = before_diet_plan[:last_index]
            
            # Now remove all duplicate client summary sections
            # The pattern will look for another Diet & Wellness Plan heading followed by Client Summary
            if "<h2>Diet &amp; Wellness Plan</h2>" in after_diet_plan and "<h3>Client Summary</h3>" in after_diet_plan:
                # Find where the duplicate Diet & Wellness Plan section starts
                dup_diet_plan_index = after_diet_plan.find("<h2>Diet &amp; Wellness Plan</h2>")
                
                # Find the next major section after the duplicate client summary
                next_major_section_match = re.search(r'<h2>', after_diet_plan[dup_diet_plan_index + len("<h2>Diet &amp; Wellness Plan</h2>"):])
                
                if next_major_section_match:
                    # Position relative to the start of the duplicate section
                    relative_position = next_major_section_match.start()
                    # Absolute position in after_diet_plan
                    absolute_position = dup_diet_plan_index + len("<h2>Diet &amp; Wellness Plan</h2>") + relative_position
                    
                    # Remove the entire duplicate client summary section
                    after_diet_plan = after_diet_plan[:dup_diet_plan_index] + after_diet_plan[absolute_position:]
                else:
                    # If no clear next section, just remove everything after the duplicate Diet & Wellness Plan
                    after_diet_plan = after_diet_plan[:dup_diet_plan_index]
            
            # Reconstruct the HTML with duplicates removed
            html_body = before_diet_plan + "<h2>Diet &amp; Wellness Plan</h2>" + after_diet_plan
    
    # Adapt meal plan headings based on client diet preferences
    # Check for any diet type in the HTML
    diet_type = "Meal"
    if "vegan" in html_body.lower():
        diet_type = "Vegan"
    elif "vegetarian" in html_body.lower():
        diet_type = "Vegetarian"
    elif "non-veg" in html_body.lower() or "non veg" in html_body.lower():
        diet_type = "Non-Vegetarian"
    
    # Update meal plan headings if they exist
    meal_plan_patterns = [
        (r'<h[23]>\s*\d+-WEEK VEGAN MEAL PLAN\s*</h[23]>', f'<h2>4-WEEK {diet_type.upper()} MEAL PLAN</h2>'),
        (r'<h[23]>\s*\d+-week vegan meal plan\s*</h[23]>', f'<h2>4-WEEK {diet_type.upper()} MEAL PLAN</h2>'),
        (r'<h[23]>\s*\d+\s*-\s*WEEK VEGAN MEAL PLAN\s*</h[23]>', f'<h2>4-WEEK {diet_type.upper()} MEAL PLAN</h2>')
    ]
    
    for pattern, replacement in meal_plan_patterns:
        html_body = re.sub(pattern, replacement, html_body, flags=re.IGNORECASE)
    
    # Replace the note about "Weeks 2, 3, and 4 follow a similar structure" with full tables
    # First check if we have a note about similar structure in weeks 2-4
    if "(Weeks 2, 3, and 4 follow a similar structure" in html_body or "structure similar to Week 1" in html_body or "other weeks follow" in html_body.lower():
        # Find the first week table to use as a template
        if "<h3>Week 1</h3>" in html_body or "<h2>Week 1</h2>" in html_body:
            # Split the HTML to locate the Week 1 table
            week_parts = re.split(r'<h[23]>Week 1</h[23]>', html_body, 1)
            
            if len(week_parts) > 1:
                before_week = week_parts[0]
                after_week = week_parts[1]
                
                # Find the end of the Week 1 table section - look for various patterns
                end_table_parts = None
                for pattern in [
                    r'<p>\(Weeks 2, 3, and 4 follow a similar structure',
                    r'<p>Weeks 2-4 follow',
                    r'<p>Other weeks follow',
                    r'<h[23]>Week 2</h[23]>'
                ]:
                    parts = re.split(pattern, after_week, 1)
                    if len(parts) > 1:
                        end_table_parts = parts
                        break
                
                # If we found a split point
                if end_table_parts and len(end_table_parts) > 1:
                    week1_table = end_table_parts[0]
                    rest_content = end_table_parts[1]
                    
                    # Remove the note about similar structure
                    if ")" in rest_content:
                        rest_content = rest_content.split(")", 1)[1]
                    
                    # Create tables for weeks 2-4 with slight variations
                    week2_table = week1_table.replace("Monday", "Monday<br>(Week 2)")
                    week2_table = week2_table.replace("Tuesday", "Tuesday<br>(Week 2)")
                    week2_table = week2_table.replace("Wednesday", "Wednesday<br>(Week 2)")
                    week2_table = week2_table.replace("Thursday", "Thursday<br>(Week 2)")
                    week2_table = week2_table.replace("Friday", "Friday<br>(Week 2)")
                    week2_table = week2_table.replace("Saturday", "Saturday<br>(Week 2)")
                    week2_table = week2_table.replace("Sunday", "Sunday<br>(Week 2)")
                    
                    week3_table = week1_table.replace("Monday", "Monday<br>(Week 3)")
                    week3_table = week3_table.replace("Tuesday", "Tuesday<br>(Week 3)")
                    week3_table = week3_table.replace("Wednesday", "Wednesday<br>(Week 3)")
                    week3_table = week3_table.replace("Thursday", "Thursday<br>(Week 3)")
                    week3_table = week3_table.replace("Friday", "Friday<br>(Week 3)")
                    week3_table = week3_table.replace("Saturday", "Saturday<br>(Week 3)")
                    week3_table = week3_table.replace("Sunday", "Sunday<br>(Week 3)")
                    
                    week4_table = week1_table.replace("Monday", "Monday<br>(Week 4)")
                    week4_table = week4_table.replace("Tuesday", "Tuesday<br>(Week 4)")
                    week4_table = week4_table.replace("Wednesday", "Wednesday<br>(Week 4)")
                    week4_table = week4_table.replace("Thursday", "Thursday<br>(Week 4)")
                    week4_table = week4_table.replace("Friday", "Friday<br>(Week 4)")
                    week4_table = week4_table.replace("Saturday", "Saturday<br>(Week 4)")
                    week4_table = week4_table.replace("Sunday", "Sunday<br>(Week 4)")
                    
                    # Add page break classes
                    week2_heading = '<div class="pagebreak"></div><h3>Week 2</h3>'
                    week3_heading = '<div class="pagebreak"></div><h3>Week 3</h3>'
                    week4_heading = '<div class="pagebreak"></div><h3>Week 4</h3>'
                    
                    # Reconstruct the HTML with all 4 weeks
                    # Check if Week 2, 3, or 4 already exists in the rest_content
                    if "<h3>Week 2</h3>" not in rest_content and "<h2>Week 2</h2>" not in rest_content:
                        html_body = before_week + '<h3>Week 1</h3>' + week1_table + \
                                    week2_heading + week2_table + \
                                    week3_heading + week3_table + \
                                    week4_heading + week4_table + \
                                    rest_content
                    else:
                        # If other weeks already exist, just keep the original content
                        html_body = before_week + '<h3>Week 1</h3>' + after_week
    
    # Get current date for the header
    current_date = datetime.now().strftime("%d %B, %Y")
    
    # Create a styled HTML document with headers and footers on every page
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
                @top-center {{
                    content: element(header);
                }}
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 9pt;
                    font-family: 'Times New Roman', Times, serif;
                }}
            }}
            
            body {{
                font-family: 'Times New Roman', Times, serif;
                line-height: 1.5;
                margin: 0;
                padding: 0;
                color: #000;
                font-size: 11pt;
            }}
            
            .header {{
                text-align: center;
                padding-bottom: 8px;
                border-bottom: 1px solid #000;
                position: running(header);
            }}
            
            .header-content {{
                display: block;
            }}
            
            .header h1 {{
                font-size: 16pt;
                margin-bottom: 5px;
                font-weight: bold;
            }}
            
            .header p {{
                font-size: 10pt;
                margin: 2px 0;
            }}
            
            .content {{
                margin-top: 1cm;
            }}
            
            h1 {{
                font-size: 16pt;
                margin-top: 15px;
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
                padding: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 10pt;
            }}
            
            td {{
                border: 1px solid #000;
                padding: 6px;
                text-align: left;
                font-size: 10pt;
            }}
            
            strong {{
                font-weight: bold;
            }}
            
            .pagebreak {{
                page-break-before: always;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <h1>HRIM Wellness Centre</h1>
                <p>503, Takshshila Apartment, Dayalaji Ashram Marg, Majura Gate, Surat - 395001, Gujarat, India</p>
                <p>Phone: +91 94279 81235 | Email: hrimwellness@gmail.com | Web: www.hrimwellness.in</p>
                <p>Date: {current_date}</p>
            </div>
        </div>
        
        <div class="content">
        {html_body}
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
        # Extract the content from the HTML - we just want the body content without styles
        content_match = re.search(r'<div class="content">(.*?)</div>\s*</body>', html, re.DOTALL)
        content = ""
        if content_match:
            content = content_match.group(1)
        else:
            # Fallback to get anything between body tags if the content div isn't found
            body_match = re.search(r'<body>(.*?)</body>', html, re.DOTALL)
            if body_match:
                content = body_match.group(1)
            else:
                # Last resort - use the whole HTML
                content = html
        
        # Create an extremely basic HTML without any CSS that might cause parsing errors
        ultra_simple_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>HRIM Wellness Centre</title>
        </head>
        <body>
            <h1 style="text-align:center">HRIM Wellness Centre</h1>
            <p style="text-align:center">
                503, Takshshila Apartment, Dayalaji Ashram Marg, Majura Gate, Surat - 395001, Gujarat, India<br>
                Phone: +91 94279 81235 | Email: hrimwellness@gmail.com | Web: www.hrimwellness.in<br>
                Date: {datetime.now().strftime("%d %B, %Y")}
            </p>
            <hr>
            {content}
        </body>
        </html>
        """
        
        # Create the PDF with absolutely minimal options
        result = pisa.CreatePDF(
            src=ultra_simple_html,
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
    except Exception as e:
        # Log the error
        logger.error(f"Exception in PDF generation: {str(e)}", exc_info=True)
        
        # Create a VERY simple fallback PDF with error message - no CSS at all
        # Escape any HTML entities in the error message
        error_message = str(e).replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Error Report</title>
        </head>
        <body>
            <h1 style="text-align:center">HRIM Wellness Centre</h1>
            <h2 style="text-align:center">Error Generating PDF</h2>
            <p>There was an error generating the PDF document. Please contact support.</p>
            <p>Error details: {error_message}</p>
        </body>
        </html>
        """
        
        # Reset BytesIO object
        pdf_data = io.BytesIO()
        
        # Try again with absolutely minimal HTML, no CSS at all
        simple_result = pisa.CreatePDF(
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
        
        # Create a unique filename for the PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{client_name.replace(' ', '_')}_wellness_plan_{timestamp}.pdf"
        pdf_key = f"jobs/{job_id}/{pdf_filename}"
        
        try:
            # Try the normal PDF generation first
            # Convert formatted response to HTML
            html = markdown_to_html(formatted_response, client_name)
            
            # Generate PDF
            pdf_bytes, pdf_data = generate_pdf_from_html(html)
        except Exception as pdf_error:
            # If normal PDF generation fails, try an ultra-simple approach
            logger.warning(f"Standard PDF generation failed: {str(pdf_error)}. Trying fallback method...")
            
            # Create a very basic fallback content
            simple_markdown = f"# HRIM Wellness Centre\n\n## Diet & Wellness Plan for {client_name}\n\n"
            
            # Add a simplified version of the client summary (key details only)
            simple_markdown += "### Client Summary\n\n"
            simple_markdown += f"* **Name**: {client_data.get('Full Name', '')}\n"
            simple_markdown += f"* **Age**: {client_data.get('Age', '35 (estimated)')}\n"
            simple_markdown += f"* **Health Goals**: {client_data.get('Primary Health Goals', 'Weight management and overall wellness')}\n\n"
            
            # Add a note about the complete plan being available
            simple_markdown += "### Note\n\n"
            simple_markdown += "The complete wellness plan could not be formatted as a PDF due to technical issues. "
            simple_markdown += "Please contact HRIM Wellness Centre to receive your complete plan.\n\n"
            simple_markdown += f"Error details: {str(pdf_error).replace('<', '&lt;').replace('>', '&gt;')}"
            
            # Convert to basic HTML and generate a simple PDF
            simple_html = markdown.markdown(simple_markdown)
            
            # Basic HTML wrapper with no CSS
            ultra_simple_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>HRIM Wellness Plan</title>
            </head>
            <body>
                {simple_html}
            </body>
            </html>
            """
            
            # Generate a minimal PDF
            pdf_data = io.BytesIO()
            result = pisa.CreatePDF(
                src=ultra_simple_html,
                dest=pdf_data,
                encoding='UTF-8'
            )
            
            pdf_data.seek(0)
            pdf_bytes = pdf_data.getvalue()
            pdf_data.seek(0)
        
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