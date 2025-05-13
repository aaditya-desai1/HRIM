"""
Format prompt lambda function.

This function prepares the client data for the Gemini API call by formatting it
into a detailed prompt that will generate a personalized wellness plan.
"""

import json
import os
import logging
import sys

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def format_gemini_prompt(client_data):
    """
    Format client data into a prompt for the Gemini API.
    
    Args:
        client_data: Dict containing client data
        
    Returns:
        Formatted prompt string
    """
    # Extract client data, defaulting to "Not provided" for missing fields
    full_name = client_data.get('Full Name', 'Not provided')
    email = client_data.get('Email', 'Not provided')
    dob = client_data.get('Date of Birth', 'Not provided')
    gender = client_data.get('Gender', 'Not provided')
    height = client_data.get('Height', 'Not provided')
    weight = client_data.get('Weight', 'Not provided')
    occupation = client_data.get('Occupation', 'Not provided')
    medical_conditions = client_data.get('Medical Conditions', 'None')
    allergies = client_data.get('Allergies or Sensitivities', 'None')
    medications = client_data.get('Current Medications', 'None')
    dietary_preference = client_data.get('Dietary Preference', 'Vegan')  # Default to Vegan
    meals_per_day = client_data.get('Meals per Day', '3')
    meal_times = client_data.get('Usual Meal Times', 'Not provided')
    cuisine = client_data.get('Cuisine Preference', 'Indian')  # Default to Indian
    foods_enjoy = client_data.get('Foods You Enjoy', 'Not provided')
    foods_dislike = client_data.get('Foods You Dislike', 'Not provided')
    activity_level = client_data.get('Activity Level', 'Not provided')
    exercise = client_data.get('Current Exercise Routine', 'Not provided')
    sleep = client_data.get('Sleep Pattern', 'Not provided')
    stress = client_data.get('Stress Level', 'Not provided')
    water = client_data.get('Daily Water Intake', 'Not provided')
    wellness_goals = client_data.get('Wellness Goals', 'Not provided')
    weight_goal = client_data.get('Weight Management Goal', 'Not provided')
    energy_concerns = client_data.get('Energy Level Concerns', 'Not provided')
    food_budget = client_data.get('Food Budget', 'Not provided')
    cooking_time = client_data.get('Available Cooking Time', 'Not provided')
    household_size = client_data.get('Household Size', 'Not provided')
    previous_plans = client_data.get('Previous Diet Plans', 'None')
    additional_info = client_data.get('Additional Information', 'None')
    
    # Construct the prompt with a detailed persona and instructions
    prompt = f"""
You are an experienced Clinical Dietician with over 25 years of experience, specializing in Indian vegan nutrition and holistic wellness. You have a deep understanding of US FDA guidelines and Indian cultural context for food and lifestyle recommendations.

# CLIENT INFORMATION:

## Personal Info:
- Full Name: {full_name}
- Date of Birth: {dob}
- Gender: {gender}
- Height: {height}
- Weight: {weight}
- Occupation: {occupation}

## Medical:
- Conditions: {medical_conditions}
- Allergies/Sensitivities: {allergies}
- Current Medications: {medications}

## Diet Habits:
- Dietary Preference: {dietary_preference}
- Meals per Day: {meals_per_day}
- Usual Meal Times: {meal_times}
- Cuisine Preference: {cuisine}
- Foods Enjoyed: {foods_enjoy}
- Foods Disliked: {foods_dislike}

## Lifestyle:
- Activity Level: {activity_level}
- Current Exercise: {exercise}
- Sleep Pattern: {sleep}
- Stress Level: {stress}
- Daily Water Intake: {water}

## Other Details:
- Wellness Goals: {wellness_goals}
- Weight Management Goal: {weight_goal}
- Energy Level Concerns: {energy_concerns}
- Food Budget: {food_budget}
- Available Cooking Time: {cooking_time}
- Household Size: {household_size}
- Previous Diet Plans: {previous_plans}
- Additional Information: {additional_info}

# DELIVERABLES:

Based on the above client information, create a comprehensive 4-week Indian vegan wellness and diet plan with the following components:

1. **4-Week Meal Plan** - Format each week in a clear tabular structure with:
   - Breakfast, Lunch, Dinner, and Snacks for each day of the week
   - Simple, quick-to-prepare meals (matching their Available Cooking Time)
   - Include quantities for one person and for family (multiply servings as needed)
   - Focus on Indian vegan options with local, seasonal ingredients
   - Ensure nutritional balance meeting their goals

2. **Weekly Daily Routine Chart** - Include:
   - Wake-up routine
   - Meal timings (matching their usual meal times)
   - Recommended physical activities (appropriate for their activity level)
   - Relaxation/stress management practices
   - Hydration schedule
   - Sleep routine
   - Present this as a structured daily timeline

3. **Weekly Grocery Lists** - For each week:
   - Organized by category (vegetables, fruits, grains, legumes, etc.)
   - Include exact quantities needed
   - Focus on affordable options (matching their food budget)
   - Include Indian names of ingredients when relevant
   - Alternative options for hard-to-find ingredients

4. **DOs & DON'Ts** - Provide:
   - At least 10 specific "DO" recommendations
   - At least 10 specific "DON'T" warnings
   - These should be personalized to their goals, conditions, and preferences

5. **Stress & Balance Tips** - For each week:
   - 3-5 specific mindfulness or stress management techniques
   - Simple yoga practices or breathing exercises
   - Mental wellness suggestions
   - Lifestyle adjustments

6. **Summary & Follow-up** - Conclude with:
   - Overview of how this plan addresses their specific goals
   - Expected timeline for results
   - Recommendations for progress tracking
   - Suggestions for long-term sustainability

Format your response in clear, structured Markdown with headings, lists, and tables for readability.

DO NOT:
- Include non-vegan ingredients
- Propose unrealistic changes to their lifestyle
- Include generic, non-personalized advice
- Skip any of the required sections
- Ask follow-up questions (use all information as provided)

Remember: This is a professional wellness plan for a real client. Make it detailed, practical, and specifically tailored to their needs and constraints.
"""
    
    return prompt

def lambda_handler(event, context):
    """
    Lambda handler function.
    
    Args:
        event: The event dict containing job_id and client_data
        context: Lambda context
        
    Returns:
        Dict containing job ID, formatted prompt, and status
    """
    try:
        # Parse the event
        if 'body' in event:
            # If coming from API Gateway
            body = json.loads(event['body'])
            job_id = body.get('job_id')
            client_data = body.get('client_data')
        else:
            # If coming from direct Lambda invocation
            job_id = event.get('job_id')
            client_data = event.get('client_data')
        
        logger.info(f"Formatting prompt for job: {job_id}")
        
        if not job_id or not client_data:
            logger.error("Missing required parameters: job_id or client_data")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Update job status
        utils.update_job_status(job_id, utils.JobStatus.FORMATTING_PROMPT)
        
        # Format the prompt
        prompt = format_gemini_prompt(client_data)
        
        # Store the formatted prompt in S3
        prompt_key = f"jobs/{job_id}/prompt.txt"
        utils.write_to_s3(utils.OUTPUT_BUCKET, prompt_key, prompt, 'text/plain')
        
        logger.info(f"Prompt formatted and stored for job: {job_id}")
        
        # Prepare result for next step
        result = {
            'job_id': job_id,
            'prompt': prompt,
            'prompt_key': prompt_key,
            'client_data': client_data,
            'status': utils.JobStatus.CALLING_AI
        }
        
        # Update job status to indicate we're moving to call AI
        utils.update_job_status(job_id, utils.JobStatus.CALLING_AI)
        
        logger.info(f"Job {job_id} proceeding to call_gemini")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error in format_prompt: {str(e)}", exc_info=True)
        
        # Update job status to failed if we have a job ID
        if 'job_id' in locals() and job_id:
            utils.update_job_status(job_id, utils.JobStatus.FAILED, str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 