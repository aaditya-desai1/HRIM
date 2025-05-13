# Output definitions for HRIM project

# Output the AWS region being used
output "aws_region" {
  description = "The AWS region where the resources are deployed"
  value       = data.aws_region.current.name
}

# Input bucket name output
output "input_bucket_name" {
  description = "The name of the S3 bucket for input data"
  value       = var.input_bucket_name
}

# Output bucket name output
output "output_bucket_name" {
  description = "The name of the S3 bucket for output PDFs and artifacts"
  value       = var.output_bucket_name
}

# Get current AWS region
data "aws_region" "current" {} 