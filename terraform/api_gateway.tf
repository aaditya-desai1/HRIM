# API Gateway for Google Form submission
resource "aws_api_gateway_rest_api" "hrim_api" {
  name        = "hrim-form-submission-api"
  description = "API for receiving Google Form submissions"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# API Resources and Methods
resource "aws_api_gateway_resource" "form_submission" {
  rest_api_id = aws_api_gateway_rest_api.hrim_api.id
  parent_id   = aws_api_gateway_rest_api.hrim_api.root_resource_id
  path_part   = "form-submission"
}

# POST method for form submissions
resource "aws_api_gateway_method" "form_submission_post" {
  rest_api_id   = aws_api_gateway_rest_api.hrim_api.id
  resource_id   = aws_api_gateway_resource.form_submission.id
  http_method   = "POST"
  authorization = "NONE"
}

# OPTIONS method for CORS support
resource "aws_api_gateway_method" "form_submission_options" {
  rest_api_id   = aws_api_gateway_rest_api.hrim_api.id
  resource_id   = aws_api_gateway_resource.form_submission.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Integration with Lambda
resource "aws_api_gateway_integration" "form_submission_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.hrim_api.id
  resource_id             = aws_api_gateway_resource.form_submission.id
  http_method             = aws_api_gateway_method.form_submission_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.form_submission.invoke_arn
}

# CORS - OPTIONS method integration
resource "aws_api_gateway_integration" "form_submission_options" {
  rest_api_id             = aws_api_gateway_rest_api.hrim_api.id
  resource_id             = aws_api_gateway_resource.form_submission.id
  http_method             = aws_api_gateway_method.form_submission_options.http_method
  type                    = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# CORS - Response for OPTIONS
resource "aws_api_gateway_method_response" "form_submission_options_200" {
  rest_api_id = aws_api_gateway_rest_api.hrim_api.id
  resource_id = aws_api_gateway_resource.form_submission.id
  http_method = aws_api_gateway_method.form_submission_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# CORS - Integration response for OPTIONS
resource "aws_api_gateway_integration_response" "form_submission_options_200" {
  rest_api_id = aws_api_gateway_rest_api.hrim_api.id
  resource_id = aws_api_gateway_resource.form_submission.id
  http_method = aws_api_gateway_method.form_submission_options.http_method
  status_code = aws_api_gateway_method_response.form_submission_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'",
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }
}

# Deploy API to a stage
resource "aws_api_gateway_deployment" "hrim_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.form_submission_lambda,
    aws_api_gateway_integration.form_submission_options
  ]
  
  rest_api_id = aws_api_gateway_rest_api.hrim_api.id
  stage_name  = var.environment
  
  # Ensure redeployment when the configuration changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.form_submission,
      aws_api_gateway_method.form_submission_post,
      aws_api_gateway_method.form_submission_options,
      aws_api_gateway_integration.form_submission_lambda,
      aws_api_gateway_integration.form_submission_options
    ]))
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Permission for API Gateway to invoke Lambda
resource "aws_lambda_permission" "apigw_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.form_submission.function_name
  principal     = "apigateway.amazonaws.com"
  
  # The /*/* portion grants access from any method on any resource
  # within the API Gateway REST API
  source_arn = "${aws_api_gateway_rest_api.hrim_api.execution_arn}/*/*"
}

# Lambda function for form_submission
resource "aws_lambda_function" "form_submission" {
  function_name    = "hrim-form-submission"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/form_submission/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/form_submission/lambda_function.zip")
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  
  # Include shared utils
  layers = var.lambda_layer_arn != "" ? [var.lambda_layer_arn] : []
  
  environment {
    variables = {
      JOB_TABLE_NAME = var.dynamodb_table_name
      INPUT_BUCKET   = var.input_bucket_name
      OUTPUT_BUCKET  = var.output_bucket_name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# Outputs for the API URL
output "api_gateway_invoke_url" {
  description = "The URL to invoke the API Gateway"
  value       = "${aws_api_gateway_deployment.hrim_api_deployment.invoke_url}/${aws_api_gateway_resource.form_submission.path_part}"
} 