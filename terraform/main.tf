provider "aws" {
  region = var.aws_region
}

# DynamoDB table for tracking jobs
resource "aws_dynamodb_table" "hrim_jobs" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "job_id"
  
  attribute {
    name = "job_id"
    type = "S"
  }
  
  tags = {
    Name        = var.dynamodb_table_name
    Environment = var.environment
    Project     = "HRIM"
  }
}

# S3 bucket for input data
resource "aws_s3_bucket" "input_bucket" {
  bucket = var.input_bucket_name
  
  tags = {
    Name        = var.input_bucket_name
    Environment = var.environment
    Project     = "HRIM"
  }
}

# S3 bucket for output data
resource "aws_s3_bucket" "output_bucket" {
  bucket = var.output_bucket_name
  
  tags = {
    Name        = var.output_bucket_name
    Environment = var.environment
    Project     = "HRIM"
  }
}

# S3 bucket encryption for input bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "input_bucket_encryption" {
  bucket = aws_s3_bucket.input_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket encryption for output bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "output_bucket_encryption" {
  bucket = aws_s3_bucket.output_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Event Notification to trigger Lambda
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.input_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.trigger_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "incoming/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_bucket]
}

# Allow S3 to invoke Lambda
resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input_bucket.arn
}

# Secret for storing API keys and credentials
resource "aws_secretsmanager_secret" "hrim_secrets" {
  name        = var.secrets_name
  description = "Secrets for the HRIM application (API keys, credentials)"
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# Initial secret values (use with caution in production)
resource "aws_secretsmanager_secret_version" "hrim_secrets_initial" {
  secret_id     = aws_secretsmanager_secret.hrim_secrets.id
  secret_string = jsonencode({
    GEMINI_API_KEY = var.gemini_api_key,
    SENDER_EMAIL   = var.sender_email
  })
}

# Create IAM role for Lambda functions
resource "aws_iam_role" "lambda_role" {
  name = "hrim_lambda_role"

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
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# Create IAM policy for Lambda functions
resource "aws_iam_policy" "lambda_policy" {
  name        = "hrim_lambda_policy"
  description = "Policy for HRIM Lambda functions"

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
        Effect   = "Allow"
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
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.hrim_jobs.arn
      },
      {
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Effect   = "Allow"
        Resource = aws_secretsmanager_secret.hrim_secrets.arn
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
          "states:StartExecution"
        ]
        Effect   = "Allow"
        Resource = var.enable_step_functions ? aws_sfn_state_machine.hrim_workflow[0].arn : "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
} 