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
  description = "Name of the S3 bucket for input data"
  type        = string
  default     = "wellness-data-input"
}

variable "output_bucket_name" {
  description = "Name of the S3 bucket for output PDFs"
  type        = string
  default     = "wellness-plan-output"
}

variable "jobs_table_name" {
  description = "Name of the DynamoDB table for tracking jobs"
  type        = string
  default     = "WellnessPlanJobs"
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda functions (MB)"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions (seconds)"
  type        = number
  default     = 300  # 5 minutes
}

variable "openai_api_key_secret_name" {
  description = "Name of the Secrets Manager secret containing the OpenAI API key"
  type        = string
  default     = "HRIM/OpenAI/ApiKey"
}

variable "whatsapp_api_secret_name" {
  description = "Name of the Secrets Manager secret containing the WhatsApp API details"
  type        = string
  default     = "HRIM/WhatsApp/ApiKey"
}

variable "sender_email" {
  description = "Email address to send emails from"
  type        = string
  default     = "noreply@example.com"
}

variable "notification_enabled" {
  description = "Whether to enable SNS notifications for job completion"
  type        = bool
  default     = true
}

variable "openai_model" {
  description = "OpenAI model to use"
  type        = string
  default     = "gpt-4o"
} 