# Step Functions state machine for the HRIM workflow
resource "aws_sfn_state_machine" "hrim_workflow" {
  count     = var.enable_step_functions ? 1 : 0
  name      = var.step_function_name
  role_arn  = aws_iam_role.step_functions_role[0].arn
  
  definition = <<EOF
{
  "Comment": "HRIM Wellness Plan Generation Workflow",
  "StartAt": "FetchData",
  "States": {
    "FetchData": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.fetch_data.arn}",
      "Next": "FormatPrompt",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ]
    },
    "FormatPrompt": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.format_prompt.arn}",
      "Next": "CallGemini",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ]
    },
    "CallGemini": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.call_gemini.arn}",
      "Next": "GeneratePDF",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 5,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ]
    },
    "GeneratePDF": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.generate_pdf.arn}",
      "Next": "UploadPDF",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ]
    },
    "UploadPDF": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.upload_pdf.arn}",
      "Next": "SendEmail",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ]
    },
    "SendEmail": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.send_email.arn}",
      "Next": "CompleteJob",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ]
    },
    "CompleteJob": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.complete_job.arn}",
      "End": true,
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ]
    },
    "HandleError": {
      "Type": "Pass",
      "Result": "Error occurred in the HRIM workflow",
      "End": true
    }
  }
}
EOF

  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# IAM role for Step Functions
resource "aws_iam_role" "step_functions_role" {
  count = var.enable_step_functions ? 1 : 0
  name  = "hrim_step_functions_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Environment = var.environment
    Project     = "HRIM"
  }
}

# IAM policy for Step Functions
resource "aws_iam_policy" "step_functions_policy" {
  count       = var.enable_step_functions ? 1 : 0
  name        = "hrim_step_functions_policy"
  description = "Policy for HRIM Step Functions state machine"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "lambda:InvokeFunction"
        ]
        Effect = "Allow"
        Resource = [
          aws_lambda_function.fetch_data.arn,
          aws_lambda_function.format_prompt.arn,
          aws_lambda_function.call_gemini.arn,
          aws_lambda_function.generate_pdf.arn,
          aws_lambda_function.upload_pdf.arn,
          aws_lambda_function.send_email.arn,
          aws_lambda_function.complete_job.arn
        ]
      }
    ]
  })
}

# Attach policy to Step Functions role
resource "aws_iam_role_policy_attachment" "step_functions_policy_attachment" {
  count      = var.enable_step_functions ? 1 : 0
  role       = aws_iam_role.step_functions_role[0].name
  policy_arn = aws_iam_policy.step_functions_policy[0].arn
} 