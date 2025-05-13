/**
 * Google Apps Script to send form responses to AWS S3 via API Gateway
 * 
 * Steps to set up:
 * 1. In Google Forms, go to "..." menu > Script editor
 * 2. Paste this code
 * 3. Replace API_ENDPOINT with your API Gateway URL
 * 4. Set up triggers (Edit > Current project's triggers) to run onFormSubmit when form is submitted
 */

// Replace with your API Gateway endpoint that connects to Lambda
const API_ENDPOINT = "https://24hhe95i09.execute-api.us-east-1.amazonaws.com/dev/form-submission";

/**
 * Handles form submission event.
 * 
 * @param {Object} e The form submission event
 */
function onFormSubmit(e) {
  try {
    const formResponse = e.response;
    const itemResponses = formResponse.getItemResponses();
    const formData = {};
    
    // Add basic response info
    formData["Submission Timestamp"] = formResponse.getTimestamp().toISOString();
    formData["Response ID"] = formResponse.getId();
    
    // Get the respondent's email
    formData["Email"] = formResponse.getRespondentEmail() || "";
    
    // Process all form responses and build JSON object
    for (let i = 0; i < itemResponses.length; i++) {
      const itemResponse = itemResponses[i];
      const question = itemResponse.getItem().getTitle();
      const answer = itemResponse.getResponse();
      
      // Format DOB if it's in array format (month, day, year)
      if (question === "Date of Birth" && Array.isArray(answer)) {
        formData["DOB"] = formatDate(answer);
      } else {
        formData[question] = answer;
      }
    }
    
    // Create a user-friendly email response message
    const userEmail = formData["Email"] || "provided email";
    let userMessage = `Thank you for your submission!\n\nYour personalized wellness plan will be created and sent to ${userEmail} shortly (usually within 15 minutes).\n\nPlease check your inbox (and spam folder) for an email with the subject "Your Personalized Wellness Plan".`;
    
    // Convert to JSON and send to AWS
    const jsonData = JSON.stringify(formData);
    const response = sendToAWS(jsonData);
    
    // Parse the response to check for success
    let responseObj;
    try {
      responseObj = JSON.parse(response);
    } catch (error) {
      Logger.log("Error parsing response: " + error.toString());
      responseObj = { message: "Error processing your submission. Please contact support." };
    }
    
    // Add success information to the log
    Logger.log("Form data sent to AWS. Response: " + response);
    Logger.log("Wellness plan will be generated and emailed to: " + userEmail);
    
    // Set a property to display success message to the user in the form response page
    const form = FormApp.getActiveForm();
    form.setConfirmationMessage(userMessage);
    
    return {
      success: true,
      userMessage: userMessage
    };
  } catch (error) {
    Logger.log("Error in onFormSubmit: " + error.toString());
    
    // Set a property to display error message to the user in the form response page
    const form = FormApp.getActiveForm();
    form.setConfirmationMessage("Thank you for your submission. We encountered an issue processing your request. Please contact support if you don't receive your wellness plan within 30 minutes.");
    
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Helper function to format date arrays into YYYY-MM-DD format.
 */
function formatDate(dateArray) {
  if (dateArray.length !== 3) return "";
  
  const month = padZero(dateArray[0]);
  const day = padZero(dateArray[1]);
  const year = dateArray[2];
  
  return year + "-" + month + "-" + day;
}

/**
 * Pad single digit numbers with a leading zero.
 */
function padZero(num) {
  return (num < 10) ? "0" + num : num;
}

/**
 * Sends JSON data to AWS API Gateway endpoint.
 * 
 * @param {string} jsonData The form data in JSON format
 * @return {string} The response from AWS
 */
function sendToAWS(jsonData) {
  const options = {
    method: "post",
    contentType: "application/json",
    payload: jsonData,
    muteHttpExceptions: true
  };
  
  try {
    const response = UrlFetchApp.fetch(API_ENDPOINT, options);
    return response.getContentText();
  } catch (error) {
    Logger.log("Error sending data to AWS: " + error.toString());
    return "Error: " + error.toString();
  }
}

/**
 * Test function to manually run the script.
 * Use this from the Google Apps Script editor to test the integration.
 */
function testSendToAWS() {
  const testData = {
    // SECTION 1: Email
    "Email": "kavita.kapoor@example.com",
    
    // SECTION 2: Personal Details
    "Full Name": "Kavita Kapoor",
    "DOB": "1975-05-15",
    "Gender": "Female",
    "WhatsApp Contact Number": "+919427981235",
    "Address": "123 Wellness Avenue, Near City Center",
    "City": "Surat",
    "PIN": "395007",
    "State": "Gujarat",
    "Country": "India",
    "Occupation": "Business Owner",
    "Marital Status": "Married",
    
    // SECTION 3: Demographic and Lifestyle Information
    "Height (in cm)": "165",
    "Current Weight (in kg)": "58",
    "Target Weight (if any)": "55",
    "Primary Health Goals": "Weight Loss, Improve Fitness & Stamina, Boost Immunity",
    
    // SECTION 4: Medical History
    "Do you have any existing medical conditions?": "Yes",
    "If yes, please specify medical conditions.": "Occasional migraines, mild hypertension",
    "Are you currently on any medications?": "Yes",
    "If yes, please specify medications": "Low-dose blood pressure medication",
    "Any allergies (food or otherwise)?": "Yes",
    "If yes, Please specify allergies.": "Dust, mild gluten sensitivity",
    "Family Medical History: (e.g. diabetes, heart disease)": "Father had diabetes, mother has hypothyroidism",
    
    // SECTION 5: Daily Routine & Lifestyle
    "Wake-Up Time": "6:30 AM",
    "Sleep Time": "10:30 PM",
    "Average Hours of Sleep": "8",
    "Work Schedule": "Fixed, Remote",
    "Physical Activity Level": "Lightly Active (Light Exercise or Office Work)",
    "Exercise Routine (if any)": "30 minute walk in the morning, yoga twice a week",
    "Stress Level": "Moderate",
    "Screen Time per Day (in Hours)": "6",
    
    // SECTION 6: Dietary Preferences and Habits
    "Dietary Preference": "Vegetarian",
    "Any Dietary Restrictions?": "Yes",
    "If yes, Please specify Dietary Restrictions": "Trying to avoid gluten and excess dairy",
    "Meals per Day": "3",
    "Snacking Habit": "Occasionally",
    "Water Intake Per Day (in Liters)": "1.5",
    "Consumption of Caffeine (Tea/Coffee) Cups Per Day": "2",
    "Frequency of Eating Out": "Weekly",
    
    // SECTION 7: Mental and Emotional Well-being
    "How often do you feel stressed?": "Sometimes",
    "Do you practice any relaxation techniques?": "Yes",
    "If yes, Specify relaxation techniques.": "Deep breathing exercises, evening meditation",
    "Hobbies and Leisure Activities (Describe)": "Reading, gardening, occasional painting",
    
    // SECTION 8: Additional Information
    "Any specif concerns or goals you would like to address?": "I would like to manage my stress better and establish a sustainable healthy eating routine that fits my busy schedule",
    "Have you followed any diet or fitness plan before?": "Yes",
    "If yes, what type and what were the results?": "Tried intermittent fasting for 3 months. Lost 3kg but couldn't maintain it long-term",
    "Food Budget": "Medium",
    "Additional Information": "I travel for work once a month for about a week. Would need portable diet options during those times. Also interested in meal prep ideas for busy weekdays."
  };
  
  const jsonData = JSON.stringify(testData);
  const response = sendToAWS(jsonData);
  Logger.log("Test response: " + response);
} 