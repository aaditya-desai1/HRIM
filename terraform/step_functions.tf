resource "aws_sfn_state_machine" "wellness_plan_workflow" {
  name     = "WellnessPlanWorkflow"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = <<EOF
{
  "Comment": "State machine for Wellness Plan generation and delivery",
  "StartAt": "FetchData",
  "States": {
    "FetchData": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.fetch_data.arn}",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "Next": "FormatPrompt"
    },
    "FormatPrompt": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.format_prompt.arn}",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "Next": "CallOpenAI"
    },
    "CallOpenAI": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.call_openai.arn}",
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
      ],
      "Next": "GeneratePDF"
    },
    "GeneratePDF": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.generate_pdf.arn}",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "Next": "UploadPDF"
    },
    "UploadPDF": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.upload_pdf.arn}",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "Next": "SendNotifications"
    },
    "SendNotifications": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "SendEmail",
          "States": {
            "SendEmail": {
              "Type": "Task",
              "Resource": "${aws_lambda_function.send_email.arn}",
              "Retry": [
                {
                  "ErrorEquals": ["States.TaskFailed"],
                  "IntervalSeconds": 3,
                  "MaxAttempts": 2,
                  "BackoffRate": 2.0
                }
              ],
              "Catch": [
                {
                  "ErrorEquals": ["States.ALL"],
                  "ResultPath": "$.error",
                  "Next": "EmailFailed"
                }
              ],
              "End": true
            },
            "EmailFailed": {
              "Type": "Pass",
              "Result": {
                "email_status": "FAILED",
                "error": "Failed to send email"
              },
              "End": true
            }
          }
        },
        {
          "StartAt": "SendWhatsApp",
          "States": {
            "SendWhatsApp": {
              "Type": "Task",
              "Resource": "${aws_lambda_function.send_whatsapp.arn}",
              "Retry": [
                {
                  "ErrorEquals": ["States.TaskFailed"],
                  "IntervalSeconds": 3,
                  "MaxAttempts": 2,
                  "BackoffRate": 2.0
                }
              ],
              "Catch": [
                {
                  "ErrorEquals": ["States.ALL"],
                  "ResultPath": "$.error",
                  "Next": "WhatsAppFailed"
                }
              ],
              "End": true
            },
            "WhatsAppFailed": {
              "Type": "Pass",
              "Result": {
                "whatsapp_status": "FAILED",
                "error": "Failed to send WhatsApp message"
              },
              "End": true
            }
          }
        }
      ],
      "Next": "CompleteJob"
    },
    "CompleteJob": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.complete_job.arn}",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "End": true
    },
    "HandleError": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.handle_error.arn}",
      "End": true
    }
  }
}
EOF

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_log_group.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  depends_on = [
    aws_lambda_function.fetch_data,
    aws_lambda_function.format_prompt,
    aws_lambda_function.call_openai,
    aws_lambda_function.generate_pdf,
    aws_lambda_function.upload_pdf,
    aws_lambda_function.send_email,
    aws_lambda_function.send_whatsapp,
    aws_lambda_function.complete_job,
    aws_lambda_function.handle_error,
    aws_cloudwatch_log_group.step_functions_log_group
  ]
}

resource "aws_cloudwatch_log_group" "step_functions_log_group" {
  name              = "/aws/states/WellnessPlanWorkflow"
  retention_in_days = 30
}

resource "aws_iam_role" "step_functions_role" {
  name = "WellnessPlanStepFunctionsRole"

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
}

resource "aws_iam_policy" "step_functions_policy" {
  name        = "WellnessPlanStepFunctionsPolicy"
  description = "Policy for Step Functions to invoke Lambda functions"

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
          aws_lambda_function.call_openai.arn,
          aws_lambda_function.generate_pdf.arn,
          aws_lambda_function.upload_pdf.arn,
          aws_lambda_function.send_email.arn,
          aws_lambda_function.send_whatsapp.arn,
          aws_lambda_function.complete_job.arn,
          aws_lambda_function.handle_error.arn
        ]
      },
      {
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutLogEvents",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_functions_policy_attachment" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = aws_iam_policy.step_functions_policy.arn
} 