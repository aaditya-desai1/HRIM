provider "aws" {
  region = var.aws_region
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  required_version = ">= 1.0.0"
}

# Make sure Secrets Manager secrets exist for API keys
# These are not created by Terraform to avoid storing sensitive data in state
# You should create these secrets manually in the AWS console

output "secrets_info" {
  value = <<EOF
Please ensure the following AWS Secrets Manager secrets exist:
1. ${var.openai_api_key_secret_name} - containing: {"api_key": "your-openai-api-key"}
2. ${var.whatsapp_api_secret_name} - containing: {"api_url": "your-whatsapp-api-url", "access_token": "your-whatsapp-access-token"}
EOF
}

output "s3_buckets" {
  value = {
    input_bucket  = aws_s3_bucket.input_bucket.bucket
    output_bucket = aws_s3_bucket.output_bucket.bucket
  }
}

output "dynamodb_table" {
  value = aws_dynamodb_table.wellness_plan_jobs.name
}

output "step_functions_arn" {
  value = aws_sfn_state_machine.wellness_plan_workflow.arn
}

output "lambda_functions" {
  value = {
    trigger_processor = aws_lambda_function.trigger_processor.function_name
    fetch_data        = aws_lambda_function.fetch_data.function_name
    format_prompt     = aws_lambda_function.format_prompt.function_name
    call_openai       = aws_lambda_function.call_openai.function_name
    generate_pdf      = aws_lambda_function.generate_pdf.function_name
    upload_pdf        = aws_lambda_function.upload_pdf.function_name
    send_email        = aws_lambda_function.send_email.function_name
    send_whatsapp     = aws_lambda_function.send_whatsapp.function_name
    complete_job      = aws_lambda_function.complete_job.function_name
    handle_error      = aws_lambda_function.handle_error.function_name
  }
}

output "sns_topic" {
  value = var.notification_enabled ? aws_sns_topic.job_completion[0].arn : "SNS notifications disabled"
} 