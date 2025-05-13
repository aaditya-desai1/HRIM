variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "input_bucket_name" {
  description = "Name of the S3 bucket for input client data"
  type        = string
  default     = "hrim-input-data"
}

variable "output_bucket_name" {
  description = "Name of the S3 bucket for output PDFs and artifacts"
  type        = string
  default     = "hrim-output-data"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for job tracking"
  type        = string
  default     = "hrim-jobs"
}

variable "secrets_name" {
  description = "Name of the Secrets Manager secret for API keys"
  type        = string
  default     = "hrim-secrets"
}

variable "lambda_functions" {
  description = "List of Lambda functions to create"
  type        = list(string)
  default     = [
    "trigger_processor",
    "fetch_data",
    "format_prompt",
    "call_gemini",
    "generate_pdf",
    "upload_pdf",
    "send_email",
    "complete_job"
  ]
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda functions (MB)"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions (seconds)"
  type        = number
  default     = 300
}

variable "sender_email" {
  description = "Verified sender email address for Amazon SES"
  type        = string
  default     = "noreply@example.com"
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Google Gemini API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "lambda_python_runtime" {
  description = "Python runtime version for Lambda functions"
  type        = string
  default     = "python3.11"
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda layer containing dependencies"
  type        = string
  default     = ""
}

variable "enable_step_functions" {
  description = "Whether to enable Step Functions workflow"
  type        = bool
  default     = true
}

variable "step_function_name" {
  description = "Name of the Step Functions state machine"
  type        = string
  default     = "hrim-workflow"
} 