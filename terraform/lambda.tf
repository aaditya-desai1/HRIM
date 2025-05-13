### IAM Role for Lambda functions ###

resource "aws_iam_role" "lambda_role" {
  name = "WellnessPlanLambdaRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "WellnessPlanLambdaPolicy"
  description = "Policy for Lambda functions to access AWS resources"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.input_bucket.arn,
          "${aws_s3_bucket.input_bucket.arn}/*",
          aws_s3_bucket.output_bucket.arn,
          "${aws_s3_bucket.output_bucket.arn}/*"
        ]
      },
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.wellness_plan_jobs.arn
      },
      {
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.openai_api_key_secret_name}*",
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.whatsapp_api_secret_name}*"
        ]
      },
      {
        Action = [
          "sns:Publish"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

### Lambda Layer for Common Dependencies ###

resource "aws_lambda_layer_version" "dependencies_layer" {
  layer_name = "hrim-dependencies-layer"
  
  compatible_runtimes = ["python3.9"]
  
  filename         = "../lambda-layer.zip"
  source_code_hash = filebase64sha256("../lambda-layer.zip")
  
  depends_on = [null_resource.build_lambda_layer]
}

resource "null_resource" "build_lambda_layer" {
  triggers = {
    requirements = filesha256("../requirements.txt")
  }

  provisioner "local-exec" {
    command = <<EOT
      mkdir -p /tmp/lambda-layer/python
      pip install -r ../requirements.txt -t /tmp/lambda-layer/python
      cd /tmp/lambda-layer && zip -r ${path.module}/../lambda-layer.zip .
    EOT
  }
}

### Lambda Functions ###

resource "aws_lambda_function" "trigger_processor" {
  function_name = "hrim-trigger-processor"
  description   = "Processes S3 events and starts the workflow"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-trigger-processor.zip"
  source_code_hash = filebase64sha256("../lambda-trigger-processor.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      STATE_MACHINE_ARN = aws_sfn_state_machine.wellness_plan_workflow.arn,
      JOBS_TABLE_NAME   = aws_dynamodb_table.wellness_plan_jobs.name,
      INPUT_BUCKET      = aws_s3_bucket.input_bucket.bucket,
      OUTPUT_BUCKET     = aws_s3_bucket.output_bucket.bucket
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.trigger_processor_log_group
  ]
}

resource "aws_cloudwatch_log_group" "trigger_processor_log_group" {
  name              = "/aws/lambda/hrim-trigger-processor"
  retention_in_days = 30
}

resource "aws_lambda_function" "fetch_data" {
  function_name = "hrim-fetch-data"
  description   = "Fetches data from S3"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-fetch-data.zip"
  source_code_hash = filebase64sha256("../lambda-fetch-data.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.wellness_plan_jobs.name,
      INPUT_BUCKET    = aws_s3_bucket.input_bucket.bucket
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.fetch_data_log_group
  ]
}

resource "aws_cloudwatch_log_group" "fetch_data_log_group" {
  name              = "/aws/lambda/hrim-fetch-data"
  retention_in_days = 30
}

resource "aws_lambda_function" "format_prompt" {
  function_name = "hrim-format-prompt"
  description   = "Formats data into a GPT prompt"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-format-prompt.zip"
  source_code_hash = filebase64sha256("../lambda-format-prompt.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.wellness_plan_jobs.name
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.format_prompt_log_group
  ]
}

resource "aws_cloudwatch_log_group" "format_prompt_log_group" {
  name              = "/aws/lambda/hrim-format-prompt"
  retention_in_days = 30
}

resource "aws_lambda_function" "call_openai" {
  function_name = "hrim-call-openai"
  description   = "Calls the OpenAI API with the prompt"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-call-openai.zip"
  source_code_hash = filebase64sha256("../lambda-call-openai.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME            = aws_dynamodb_table.wellness_plan_jobs.name,
      OPENAI_API_KEY_SECRET_NAME = var.openai_api_key_secret_name,
      OPENAI_MODEL               = var.openai_model
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.call_openai_log_group
  ]
}

resource "aws_cloudwatch_log_group" "call_openai_log_group" {
  name              = "/aws/lambda/hrim-call-openai"
  retention_in_days = 30
}

resource "aws_lambda_function" "generate_pdf" {
  function_name = "hrim-generate-pdf"
  description   = "Generates a PDF from the OpenAI response"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-generate-pdf.zip"
  source_code_hash = filebase64sha256("../lambda-generate-pdf.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.wellness_plan_jobs.name
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.generate_pdf_log_group
  ]
}

resource "aws_cloudwatch_log_group" "generate_pdf_log_group" {
  name              = "/aws/lambda/hrim-generate-pdf"
  retention_in_days = 30
}

resource "aws_lambda_function" "upload_pdf" {
  function_name = "hrim-upload-pdf"
  description   = "Uploads the PDF to S3"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-upload-pdf.zip"
  source_code_hash = filebase64sha256("../lambda-upload-pdf.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.wellness_plan_jobs.name,
      OUTPUT_BUCKET   = aws_s3_bucket.output_bucket.bucket
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.upload_pdf_log_group
  ]
}

resource "aws_cloudwatch_log_group" "upload_pdf_log_group" {
  name              = "/aws/lambda/hrim-upload-pdf"
  retention_in_days = 30
}

resource "aws_lambda_function" "send_email" {
  function_name = "hrim-send-email"
  description   = "Sends the PDF via email"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-send-email.zip"
  source_code_hash = filebase64sha256("../lambda-send-email.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME = aws_dynamodb_table.wellness_plan_jobs.name,
      SENDER_EMAIL    = var.sender_email,
      EMAIL_SUBJECT   = "Your Personalized Wellness Plan"
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.send_email_log_group
  ]
}

resource "aws_cloudwatch_log_group" "send_email_log_group" {
  name              = "/aws/lambda/hrim-send-email"
  retention_in_days = 30
}

resource "aws_lambda_function" "send_whatsapp" {
  function_name = "hrim-send-whatsapp"
  description   = "Sends the PDF via WhatsApp"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-send-whatsapp.zip"
  source_code_hash = filebase64sha256("../lambda-send-whatsapp.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME         = aws_dynamodb_table.wellness_plan_jobs.name,
      WHATSAPP_API_SECRET_NAME = var.whatsapp_api_secret_name
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.send_whatsapp_log_group
  ]
}

resource "aws_cloudwatch_log_group" "send_whatsapp_log_group" {
  name              = "/aws/lambda/hrim-send-whatsapp"
  retention_in_days = 30
}

resource "aws_lambda_function" "complete_job" {
  function_name = "hrim-complete-job"
  description   = "Completes the job and updates status"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-complete-job.zip"
  source_code_hash = filebase64sha256("../lambda-complete-job.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME       = aws_dynamodb_table.wellness_plan_jobs.name,
      NOTIFICATION_TOPIC_ARN = var.notification_enabled ? aws_sns_topic.job_completion[0].arn : ""
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.complete_job_log_group
  ]
}

resource "aws_cloudwatch_log_group" "complete_job_log_group" {
  name              = "/aws/lambda/hrim-complete-job"
  retention_in_days = 30
}

resource "aws_lambda_function" "handle_error" {
  function_name = "hrim-handle-error"
  description   = "Handles errors in the workflow"
  
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"
  role    = aws_iam_role.lambda_role.arn
  
  filename         = "../lambda-handle-error.zip"
  source_code_hash = filebase64sha256("../lambda-handle-error.zip")
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size
  
  layers = [aws_lambda_layer_version.dependencies_layer.arn]
  
  environment {
    variables = {
      JOBS_TABLE_NAME       = aws_dynamodb_table.wellness_plan_jobs.name,
      NOTIFICATION_TOPIC_ARN = var.notification_enabled ? aws_sns_topic.job_completion[0].arn : ""
    }
  }
  
  depends_on = [
    null_resource.build_lambda_functions,
    aws_cloudwatch_log_group.handle_error_log_group
  ]
}

resource "aws_cloudwatch_log_group" "handle_error_log_group" {
  name              = "/aws/lambda/hrim-handle-error"
  retention_in_days = 30
}

### Build Lambda Functions ###

resource "null_resource" "build_lambda_functions" {
  triggers = {
    lambda_code = join(",", [
      filesha256("../src/lambda/utils.py"),
      filesha256("../src/lambda/trigger_processor/lambda_function.py"),
      filesha256("../src/lambda/fetch_data/lambda_function.py"),
      filesha256("../src/lambda/format_prompt/lambda_function.py"),
      filesha256("../src/lambda/call_openai/lambda_function.py"),
      filesha256("../src/lambda/generate_pdf/lambda_function.py"),
      filesha256("../src/lambda/upload_pdf/lambda_function.py"),
      filesha256("../src/lambda/send_email/lambda_function.py"),
      filesha256("../src/lambda/send_whatsapp/lambda_function.py"),
      filesha256("../src/lambda/complete_job/lambda_function.py")
    ])
  }

  provisioner "local-exec" {
    command = <<EOT
      # Build trigger_processor Lambda
      cd ../src/lambda/trigger_processor && zip -r ${path.module}/../lambda-trigger-processor.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-trigger-processor.zip lambda/utils.py
      
      # Build fetch_data Lambda
      cd ../src/lambda/fetch_data && zip -r ${path.module}/../lambda-fetch-data.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-fetch-data.zip lambda/utils.py
      
      # Build format_prompt Lambda
      cd ../src/lambda/format_prompt && zip -r ${path.module}/../lambda-format-prompt.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-format-prompt.zip lambda/utils.py
      
      # Build call_openai Lambda
      cd ../src/lambda/call_openai && zip -r ${path.module}/../lambda-call-openai.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-call-openai.zip lambda/utils.py
      
      # Build generate_pdf Lambda
      cd ../src/lambda/generate_pdf && zip -r ${path.module}/../lambda-generate-pdf.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-generate-pdf.zip lambda/utils.py
      
      # Build upload_pdf Lambda
      cd ../src/lambda/upload_pdf && zip -r ${path.module}/../lambda-upload-pdf.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-upload-pdf.zip lambda/utils.py
      
      # Build send_email Lambda
      cd ../src/lambda/send_email && zip -r ${path.module}/../lambda-send-email.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-send-email.zip lambda/utils.py
      
      # Build send_whatsapp Lambda
      cd ../src/lambda/send_whatsapp && zip -r ${path.module}/../lambda-send-whatsapp.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-send-whatsapp.zip lambda/utils.py
      
      # Build complete_job Lambda
      cd ../src/lambda/complete_job && zip -r ${path.module}/../lambda-complete-job.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-complete-job.zip lambda/utils.py
      
      # Build handle_error Lambda (create a simple error handler)
      mkdir -p ../src/lambda/handle_error
      echo 'import json
import os
import sys
import logging
import boto3

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to handle errors from the Step Functions workflow.
    
    Args:
        event (dict): Input event containing error details
        context (LambdaContext): Lambda context
        
    Returns:
        dict: Error handling result
    """
    logger.error(f"Received error event: {json.dumps(event)}")
    
    try:
        # Extract information from the event
        error = event.get("error", {})
        job_id = event.get("job_id")
        
        if not job_id:
            # Try to extract job_id from other parts of the event
            for key in event:
                if isinstance(event[key], dict) and "job_id" in event[key]:
                    job_id = event[key]["job_id"]
                    break
        
        if job_id:
            error_message = str(error) if error else "Unknown error in Step Functions workflow"
            utils.handle_error(job_id, error_message, event)
            
            # Send notification if SNS topic is configured
            sns_topic_arn = os.environ.get("NOTIFICATION_TOPIC_ARN")
            if sns_topic_arn:
                try:
                    sns = boto3.client("sns")
                    sns.publish(
                        TopicArn=sns_topic_arn,
                        Subject=f"Error in Wellness Plan Workflow - Job {job_id}",
                        Message=json.dumps({
                            "job_id": job_id,
                            "error": error_message,
                            "event": event
                        })
                    )
                except Exception as sns_error:
                    logger.error(f"Failed to send SNS notification: {str(sns_error)}")
        else:
            logger.error("Could not find job_id in the error event")
        
        return {
            "status": "ERROR_HANDLED",
            "job_id": job_id,
            "error": error
        }
    
    except Exception as e:
        logger.error(f"Error in handle_error: {str(e)}")
        return {
            "status": "ERROR_HANDLING_FAILED",
            "error": str(e)
        }' > ../src/lambda/handle_error/lambda_function.py
      
      cd ../src/lambda/handle_error && zip -r ${path.module}/../lambda-handle-error.zip lambda_function.py
      cd ../.. && zip -r ${path.module}/../lambda-handle-error.zip lambda/utils.py
    EOT
  }
}

### SNS Topic for Notifications ###

resource "aws_sns_topic" "job_completion" {
  count = var.notification_enabled ? 1 : 0
  
  name = "WellnessPlanJobCompletion"
  
  tags = {
    Name        = "WellnessPlanJobCompletion"
    Environment = var.environment
  }
} 