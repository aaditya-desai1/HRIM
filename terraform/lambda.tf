# Lambda function for trigger_processor
resource "aws_lambda_function" "trigger_processor" {
  function_name    = "hrim-trigger-processor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/trigger_processor/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/trigger_processor/lambda_function.zip")
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  
  # Include shared utils
  layers = var.lambda_layer_arn != "" ? [var.lambda_layer_arn] : []
  
  environment {
    variables = {
      JOB_TABLE_NAME     = var.dynamodb_table_name
      INPUT_BUCKET       = var.input_bucket_name
      OUTPUT_BUCKET      = var.output_bucket_name
      STEP_FUNCTION_ARN  = var.enable_step_functions ? aws_sfn_state_machine.hrim_workflow[0].arn : ""
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# Lambda function for fetch_data
resource "aws_lambda_function" "fetch_data" {
  function_name    = "hrim-fetch-data"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/fetch_data/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/fetch_data/lambda_function.zip")
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

# Lambda function for format_prompt
resource "aws_lambda_function" "format_prompt" {
  function_name    = "hrim-format-prompt"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/format_prompt/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/format_prompt/lambda_function.zip")
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  
  # Include shared utils
  layers = var.lambda_layer_arn != "" ? [var.lambda_layer_arn] : []
  
  environment {
    variables = {
      JOB_TABLE_NAME = var.dynamodb_table_name
      INPUT_BUCKET   = var.input_bucket_name
      OUTPUT_BUCKET  = var.output_bucket_name
      PROMPT_FILE_KEY = "templates/prompt.txt"
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# Lambda function for call_gemini
resource "aws_lambda_function" "call_gemini" {
  function_name    = "hrim-call-gemini"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/call_gemini/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/call_gemini/lambda_function.zip")
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  
  # Include shared utils
  layers = var.lambda_layer_arn != "" ? [var.lambda_layer_arn] : []
  
  environment {
    variables = {
      JOB_TABLE_NAME  = var.dynamodb_table_name
      INPUT_BUCKET    = var.input_bucket_name
      OUTPUT_BUCKET   = var.output_bucket_name
      GEMINI_API_KEY  = var.gemini_api_key
      SECRETS_NAME    = var.secrets_name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# Lambda function for generate_pdf
resource "aws_lambda_function" "generate_pdf" {
  function_name    = "hrim-generate-pdf"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/generate_pdf/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/generate_pdf/lambda_function.zip")
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

# Lambda function for upload_pdf
resource "aws_lambda_function" "upload_pdf" {
  function_name    = "hrim-upload-pdf"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/upload_pdf/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/upload_pdf/lambda_function.zip")
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

# Lambda function for send_email
resource "aws_lambda_function" "send_email" {
  function_name    = "hrim-send-email"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/send_email/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/send_email/lambda_function.zip")
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  
  # Include shared utils
  layers = var.lambda_layer_arn != "" ? [var.lambda_layer_arn] : []
  
  environment {
    variables = {
      JOB_TABLE_NAME = var.dynamodb_table_name
      INPUT_BUCKET   = var.input_bucket_name
      OUTPUT_BUCKET  = var.output_bucket_name
      SENDER_EMAIL   = var.sender_email
      SECRETS_NAME   = var.secrets_name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# Lambda function for complete_job
resource "aws_lambda_function" "complete_job" {
  function_name    = "hrim-complete-job"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_python_runtime
  filename         = "../src/lambda/complete_job/lambda_function.zip"
  source_code_hash = filebase64sha256("../src/lambda/complete_job/lambda_function.zip")
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