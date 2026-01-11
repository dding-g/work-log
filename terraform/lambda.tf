# ============================================================
# Lambda 함수 (ZIP 배포)
# ============================================================

resource "aws_lambda_function" "main" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_execution.arn
  package_type  = "Zip"

  # ZIP 파일 배포
  filename         = "${path.module}/lambda_placeholder.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_placeholder.zip")
  handler          = "core.lambda_handler.handler"
  runtime          = "python3.11"

  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout
  architectures = [var.lambda_architecture]

  environment {
    variables = {
      ENVIRONMENT       = "production"
      OPENAI_API_KEY    = var.openai_api_key
      ANTHROPIC_API_KEY = var.anthropic_api_key
      GITHUB_TOKEN      = var.github_token
      GITHUB_OWNER      = var.github_owner
      GITHUB_REPO       = var.github_repo
      S3_BUCKET_NAME    = aws_s3_bucket.worklog.bucket
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      USE_AI_SUMMARY    = "true"
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.lambda.name
  }

  tags = {
    Name = "${var.project_name}-lambda"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_cloudwatch_log_group.lambda,
    aws_s3_bucket.worklog
  ]

  # CI/CD에서 코드 업데이트하므로 변경 무시
  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# ============================================================
# Lambda Function URL
# ============================================================

resource "aws_lambda_function_url" "main" {
  function_name      = aws_lambda_function.main.function_name
  authorization_type = "NONE" # 퍼블릭 액세스

  cors {
    allow_credentials = true
    allow_headers     = ["*"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    expose_headers    = ["*"]
    max_age           = 86400
  }
}

# ============================================================
# Lambda 퍼미션 (Function URL 호출 허용)
# ============================================================

resource "aws_lambda_permission" "function_url" {
  statement_id           = "AllowFunctionURLInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.main.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
