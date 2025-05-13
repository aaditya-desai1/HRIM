import json
import os
import sys
import logging

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to format the client data into a GPT-4o prompt.
    
    Args:
        event (dict): Input event containing job_id and client_data
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Formatted prompt and job ID
    """
    logger.info(f"Received event for prompt formatting")
    
    try:
        # Get required parameters from event
        job_id = event.get('job_id')
        client_data = event.get('client_data')
        
        if not all([job_id, client_data]):
            error_message = "Missing required parameters in event"
            logger.error(error_message)
            return {
                'statusCode': 400,
                'error': error_message
            }
        
        # Update job status
        utils.update_job_status(job_id, 'FORMATTING_PROMPT')
        
        # Extract client information from the data
        # This is just a template - adjust field mappings based on actual Google Form structure
        client_info = {
            # Personal Info
            "full_name": client_data.get("Full Name", "User Input Missing: Full Name"),
            "dob": client_data.get("Date of Birth", "User Input Missing: DOB"),
            "gender": client_data.get("Gender", "User Input Missing: Gender"),
            "height": client_data.get("Height", "User Input Missing: Height"),
            "weight": client_data.get("Weight", "User Input Missing: Weight"),
            "occupation": client_data.get("Occupation", "User Input Missing: Occupation"),
            
            # Medical
            "medical_conditions": client_data.get("Medical Conditions", "None reported"),
            "allergies": client_data.get("Allergies or Sensitivities", "None reported"),
            "medications": client_data.get("Current Medications", "None reported"),
            
            # Diet Habits
            "diet_preference": client_data.get("Dietary Preference", "Vegan"),
            "meals_per_day": client_data.get("Meals per Day", "3"),
            "usual_meal_times": client_data.get("Usual Meal Times", "User Input Missing: Meal Times"),
            "cuisine_preference": client_data.get("Cuisine Preference", "Indian"),
            "likes": client_data.get("Foods You Enjoy", "User Input Missing: Food Likes"),
            "dislikes": client_data.get("Foods You Dislike", "User Input Missing: Food Dislikes"),
            
            # Lifestyle
            "activity_level": client_data.get("Activity Level", "User Input Missing: Activity Level"),
            "exercise_routine": client_data.get("Current Exercise Routine", "None reported"),
            "sleep_pattern": client_data.get("Sleep Pattern", "User Input Missing: Sleep Pattern"),
            "stress_level": client_data.get("Stress Level", "User Input Missing: Stress Level"),
            "water_intake": client_data.get("Daily Water Intake", "User Input Missing: Water Intake"),
            
            # Nutritional Goals
            "wellness_goals": client_data.get("Wellness Goals", "User Input Missing: Wellness Goals"),
            "weight_goal": client_data.get("Weight Management Goal", "User Input Missing: Weight Goal"),
            "energy_issues": client_data.get("Energy Level Concerns", "None reported"),
            
            # Other Details
            "food_budget": client_data.get("Food Budget", "Medium"),
            "cooking_time": client_data.get("Available Cooking Time", "User Input Missing: Cooking Time"),
            "household_size": client_data.get("Household Size", "1"),
            "previous_diets": client_data.get("Previous Diet Plans", "None reported"),
            "additional_info": client_data.get("Additional Information", "None provided")
        }
        
        # Format the prompt according to the detailed requirements in the specification
        prompt = construct_gpt_prompt(client_info)
        
        logger.info(f"Successfully formatted prompt for job {job_id}")
        
        # Return the formatted prompt and job ID for the next step
        return {
            'job_id': job_id,
            'formatted_prompt': prompt
        }
    
    except Exception as e:
        error_message = f"Error in format_prompt: {str(e)}"
        logger.error(error_message)
        if 'job_id' in locals():
            utils.handle_error(job_id, error_message)
        return {
            'statusCode': 500,
            'error': error_message
        }

def construct_gpt_prompt(client_info):
    """
    Construct a detailed prompt for GPT-4o based on client information.
    
    Args:
        client_info (dict): Extracted client information
        
    Returns:
        str: Formatted GPT-4o prompt
    """
    # Construct the system role message
    system_message = f"""
You are a Clinical Dietician with over 25 years of experience, certified by the US FDA, specializing in vegan Indian nutrition. You create personalized wellness plans tailored to individual needs. Your expertise includes creating detailed Indian vegan meal plans that are nutritionally balanced, practical, and culturally appropriate.
"""

    # Construct the user message with detailed instructions and client data
    user_message = f"""
# OBJECTIVE
Create a personalized 4-week Indian vegan diet & wellness plan for {client_info['full_name']}.

# INPUT
I'm providing the client's details - organize the plan into a comprehensive package with 4-week meal plans, routine charts, and grocery lists.

## Personal Info
- Full Name: {client_info['full_name']}
- DOB: {client_info['dob']}
- Gender: {client_info['gender']}
- Height: {client_info['height']}
- Weight: {client_info['weight']}
- Occupation: {client_info['occupation']}

## Medical
- Medical Conditions: {client_info['medical_conditions']}
- Allergies/Sensitivities: {client_info['allergies']}
- Current Medications: {client_info['medications']}

## Diet Habits
- Dietary Preference: Indian Vegan
- Meals per Day: {client_info['meals_per_day']}
- Usual Meal Times: {client_info['usual_meal_times']}
- Cuisine Preference: {client_info['cuisine_preference']}
- Foods You Enjoy: {client_info['likes']}
- Foods You Dislike: {client_info['dislikes']}

## Lifestyle
- Activity Level: {client_info['activity_level']}
- Current Exercise Routine: {client_info['exercise_routine']}
- Sleep Pattern: {client_info['sleep_pattern']}
- Stress Level: {client_info['stress_level']}
- Daily Water Intake: {client_info['water_intake']}

## Nutritional Goals
- Wellness Goals: {client_info['wellness_goals']}
- Weight Management Goal: {client_info['weight_goal']}
- Energy Level Concerns: {client_info['energy_issues']}

## Other Details
- Food Budget: {client_info['food_budget']}
- Available Cooking Time: {client_info['cooking_time']}
- Household Size: {client_info['household_size']}
- Previous Diet Plans: {client_info['previous_diets']}
- Additional Information: {client_info['additional_info']}

# DELIVERABLES
Create the complete plan with these sections (all must be included):

## 1. Four-Week Meal Plan
- Create 7-day meal plans for 4 weeks (Weeks 1-4)
- For EACH meal, provide:
  * Recipe title
  * Short ingredient list
  * Brief preparation steps
  * Quantities for 1 person AND for a family (4 servings)
- Each day must include breakfast, lunch, dinner, and 2 nutrient-dense snacks
- Ensure all recipes are 100% vegan, Indian cuisine
- Focus on quick, practical recipes (under 30 minutes)
- Include traditional Indian ingredients available at standard Indian markets

## 2. Weekly Daily Routine Chart
- Create ONE detailed daily routine chart for EACH week
- Include times for:
  * Meals and hydration
  * Physical activities appropriate for their fitness level
  * Rest periods
  * Mindfulness practices
  * Sleep schedule recommendations

## 3. Weekly Grocery Lists
- Provide FOUR separate grocery lists (one for each week)
- Include exact quantities needed for each ingredient
- Organize by categories (vegetables, fruits, grains, spices, etc.)
- List should align perfectly with the meal plan for that week

## 4. DOs & DON'Ts
- Provide specific recommendations based on their goals and health conditions
- Include both dietary and lifestyle guidelines
- List at least 10 specific items in each category

## 5. Stress & Balance Tips
- For EACH of the 4 weeks, provide 3-5 unique mindfulness or stress management techniques
- Include breathing exercises, meditation practices, or yoga poses suitable for their level
- Explain benefits and ideal times to practice each technique

## 6. Summary & Follow-up
- Summarize how this plan addresses their specific goals
- Recommend when they should reassess their progress
- Suggest 3-5 measurable indicators they can track to monitor success

# IMPORTANT CONSTRAINTS
- DO NOT ask follow-up questions - use all input exactly as given
- DO NOT skip any of the requested sections - all must be included
- DO NOT include non-vegan items (no dairy, eggs, honey, or animal products)
- DO NOT suggest generic plans - this must be highly personalized to their specific data
- DO NOT include any external references, links, or citations
- DO NOT suggest they consult other professionals before starting
- DO make reasonable estimations for any missing data points rather than pointing them out
- DO ensure all meal plans are 100% vegetarian (plant-based)
- DO consider Indian cultural context for all food recommendations
- DO emphasize mindful eating practices throughout

# OUTPUT FORMAT
Provide the complete wellness plan as a structured, comprehensive document following the exact sections specified in DELIVERABLES.
"""

    # Full prompt
    return {
        "system": system_message.strip(),
        "user": user_message.strip()
    } 