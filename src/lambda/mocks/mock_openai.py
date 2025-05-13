import json
import os
import logging
from dataclasses import dataclass

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class MockMessage:
    role: str
    content: str

@dataclass
class MockChoice:
    message: MockMessage
    index: int = 0
    finish_reason: str = "stop"

@dataclass
class MockChatCompletion:
    id: str = "mock-chatcmpl-123456789"
    object: str = "chat.completion"
    created: int = 1625097693
    model: str = "gpt-4o-mock"
    choices: list = None
    
    def __post_init__(self):
        if self.choices is None:
            self.choices = []

def load_mock_response(prompt_content):
    """Load appropriate mock response based on prompt content."""
    try:
        # Determine which mock response to return based on prompt content
        mock_response_path = os.path.join(
            os.path.dirname(__file__), 
            "mock_responses", 
            "wellness_plan.txt"
        )
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(mock_response_path), exist_ok=True)
        
        # Check if file exists, if not create a basic mock response
        if not os.path.exists(mock_response_path):
            logger.info(f"Creating mock response file at {mock_response_path}")
            with open(mock_response_path, 'w') as f:
                f.write(DEFAULT_MOCK_RESPONSE)
                
        with open(mock_response_path, 'r') as f:
            content = f.read()
            
        return content
    except Exception as e:
        logger.error(f"Error loading mock response: {str(e)}")
        return DEFAULT_MOCK_RESPONSE

class MockOpenAI:
    """Mock implementation of the OpenAI client."""
    
    class MockChatCompletions:
        @staticmethod
        def create(model, messages, temperature=0.7, max_tokens=4000, top_p=1.0, frequency_penalty=0.0, presence_penalty=0.0):
            """Simulate OpenAI chat completions API."""
            logger.info(f"Mock OpenAI API call with model: {model}")
            
            # Extract the user prompt
            user_message = next((m for m in messages if m["role"] == "user"), {"content": ""})
            prompt_content = user_message.get("content", "")
            
            # Get the appropriate mock response
            response_text = load_mock_response(prompt_content)
            
            # Create mock response object
            message = MockMessage(role="assistant", content=response_text)
            choice = MockChoice(message=message)
            completion = MockChatCompletion(choices=[choice])
            
            logger.info("Returning mock OpenAI response")
            return completion

# Default mock wellness plan response
DEFAULT_MOCK_RESPONSE = """# Four-Week Meal Plan

## Week 1 Meal Plan:

### Monday
- **Breakfast**: Masala Oats with Almonds and Fresh Fruits
  - Ingredients: 1/2 cup rolled oats, 1 tsp oil, 1/4 tsp cumin seeds, 1/4 tsp mustard seeds, 1 small chopped onion, 1/4 cup mixed vegetables, salt to taste, 1/4 tsp turmeric, 1/2 tsp garam masala, 1 tbsp chopped coriander, 5 almonds, 1/2 cup seasonal fruits
  - Preparation: Dry roast oats for 2 minutes. In a pan, add oil, cumin, mustard seeds. Add chopped onions, vegetables, spices and cook for 3-4 minutes. Add 1 cup water, bring to boil, add oats and cook for 2 minutes. Top with almonds and fruits.

- **Lunch**: Rajma Chawal with Jeera Raita
  - Ingredients: 1/2 cup soaked kidney beans, 1/2 cup rice, 1 small chopped onion, 1 small chopped tomato, 1 tsp ginger-garlic paste, 1/2 tsp cumin powder, 1/2 tsp coriander powder, 1/4 tsp turmeric, 1/2 cup yogurt, 1/4 tsp roasted cumin powder
  - Preparation: Pressure cook rajma. In a pan, sauté onions, ginger-garlic paste, add tomatoes and spices. Add cooked rajma and simmer for 10 minutes. Cook rice separately. For raita, mix yogurt with roasted cumin and salt.

- **Dinner**: Roti with Palak Tofu Curry
  - Ingredients: 2 whole wheat rotis, 1 cup spinach, 100g firm tofu, 1 small chopped onion, 1 tsp ginger-garlic paste, 1/2 tsp cumin seeds, 1/4 tsp turmeric, 1/2 tsp garam masala
  - Preparation: Blanch spinach and blend to paste. In a pan, sauté cumin seeds, onions, ginger-garlic paste. Add spices, spinach paste, and tofu cubes. Cook for 5-7 minutes. Serve with hot rotis.

- **Snack 1**: Chickpea Chaat
  - Ingredients: 1/2 cup boiled chickpeas, 1/4 cup chopped cucumber, 1/4 cup chopped tomatoes, 1 tbsp chopped coriander, 1 tsp chaat masala, 1/2 lemon juice
  - Preparation: Mix all ingredients together and serve fresh.

- **Snack 2**: Apple with Peanut Butter
  - Ingredients: 1 medium apple, 1 tbsp peanut butter
  - Preparation: Slice apple and serve with peanut butter.

[Content continues with remaining weeks...]

## Weekly Daily Routine Chart

### Week 1 Daily Routine:
- 6:30 AM: Wake up, drink a glass of warm water with lemon
- 7:00 AM: 15 minutes light stretching or yoga
- 8:00 AM: Breakfast
- 10:00 AM: Hydrate (1 glass water)
- 11:00 AM: Mid-morning snack
- 1:00 PM: Lunch followed by a 10-minute walk
- 3:00 PM: Hydrate (1 glass water)
- 4:00 PM: Afternoon snack
- 5:00 PM: 30-minute walking (increase pace gradually)
- 7:00 PM: Hydrate (1 glass water)
- 8:00 PM: Dinner
- 9:00 PM: 10 minutes meditation or deep breathing
- 10:00 PM: Screen-free time
- 11:00 PM: Bedtime

[Content continues with remaining sections...]

## DOs:
- DO include protein-rich foods like lentils, chickpeas, and tofu in every meal
- DO incorporate calcium-rich foods like fortified plant milks, sesame seeds, and leafy greens daily
- DO drink at least 8 glasses of water throughout the day
- DO practice mindful eating by chewing slowly and avoiding distractions
- DO include a variety of colorful vegetables and fruits daily for essential nutrients
- DO consume small, frequent meals to maintain energy levels
- DO include healthy fats from nuts, seeds, and avocados
- DO practice stress-reduction techniques like deep breathing or meditation daily
- DO ensure adequate B12 intake through fortified foods or supplements
- DO maintain a consistent sleep schedule of 7-8 hours per night

## DON'Ts:
- DON'T skip meals, especially breakfast
- DON'T consume caffeine after 2 PM as it may affect sleep quality
- DON'T eat heavy meals within 2 hours of bedtime
- DON'T overuse salt in your cooking as it may contribute to bloating
- DON'T rely on processed vegan foods with high sodium content
- DON'T consume sugary beverages or excessive fruit juices
- DON'T multitask while eating as it leads to poor digestion
- DON'T ignore hunger or fullness cues from your body
- DON'T compare your progress with others - focus on your personal journey
- DON'T forget to take vitamin D supplement, especially with limited sun exposure

## Summary & Follow-up

This personalized wellness plan addresses Kavita's goals of weight gain, boosting immunity, reducing stress, and improving sleep quality through a balanced approach to nutrition and lifestyle. The plan incorporates nutrient-dense Indian vegan meals with adequate protein, complex carbohydrates and healthy fats to support weight gain. Stress reduction techniques and sleep hygiene practices are integrated into the daily routine to address high stress levels and improve sleep quality.

Kavita should reassess her progress after completing the 4-week plan. Key indicators to track include:
1. Weight changes (aiming for healthy gain of 0.5-1 kg per month)
2. Energy levels throughout the day
3. Sleep quality and duration
4. Stress levels on a scale of 1-10
5. Compliance with meal timing and hydration goals

After completing this initial 4-week plan, Kavita may benefit from gradually increasing physical activity to build muscle mass while continuing the nutritional approach outlined here.""" 