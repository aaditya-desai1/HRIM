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
      if (question === "DOB" && Array.isArray(answer)) {
        formData[question] = formatDate(answer);
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
    "Full Name": "Test User",
    "Email": "test@example.com",
    "DOB": "1990-01-01",
    "Gender": "Female",
    "Height": "165 cm",
    "Weight": "60 kg",
    "Occupation": "Software Engineer",
    "Medical Conditions": "None",
    "Allergies or Sensitivities": "None",
    "Current Medications": "None",
    "Dietary Preference": "Vegan",
    "Meals per Day": "3",
    "Usual Meal Times (Breakfast)": "8:00 AM",
    "Usual Meal Times (Lunch)": "1:00 PM",
    "Usual Meal Times (Dinner)": "7:00 PM",
    "Cuisine Preference": "Indian",
    "Food You Enjoy": "Lentils, rice, vegetables",
    "Foods you Dislike": "Bitter gourd",
    "Activity Level": "Moderate",
    "Current Exercise Routine": "30 minute walk daily",
    "Sleep Pattern": "11pm to 7am",
    "Stress Level": "Moderate",
    "Daily Water Intake": "2 liters",
    "Wellness Goals": "Increase energy, maintain weight",
    "Weight Management Goal": "Maintain current weight",
    "Energy Level Concerns": "Low energy in afternoons",
    "Food Budget": "Medium",
    "Available Cooking Time": "30-45 minutes per meal",
    "Household Size": "2",
    "Previous Diet Plans": "None",
    "Additional Information": "I work long hours and need simple recipes"
  };
  
  const jsonData = JSON.stringify(testData);
  const response = sendToAWS(jsonData);
  Logger.log("Test response: " + response);
} 