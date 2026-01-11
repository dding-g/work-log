# ============================================================
# Lambda 출력
# ============================================================

output "lambda_function_name" {
  description = "Lambda 함수 이름"
  value       = aws_lambda_function.main.function_name
}

output "lambda_function_arn" {
  description = "Lambda 함수 ARN"
  value       = aws_lambda_function.main.arn
}

output "lambda_function_url" {
  description = "Lambda Function URL (API 엔드포인트)"
  value       = aws_lambda_function_url.main.function_url
}

# ============================================================
# S3 출력
# ============================================================

output "s3_bucket_name" {
  description = "S3 버킷 이름"
  value       = aws_s3_bucket.worklog.bucket
}

output "s3_bucket_arn" {
  description = "S3 버킷 ARN"
  value       = aws_s3_bucket.worklog.arn
}

# ============================================================
# EventBridge 출력
# ============================================================

output "eventbridge_rule_name" {
  description = "EventBridge 스케줄 규칙 이름"
  value       = aws_cloudwatch_event_rule.daily_worklog.name
}

output "eventbridge_rule_arn" {
  description = "EventBridge 스케줄 규칙 ARN"
  value       = aws_cloudwatch_event_rule.daily_worklog.arn
}

# ============================================================
# IAM 출력
# ============================================================

output "lambda_role_arn" {
  description = "Lambda 실행 역할 ARN"
  value       = aws_iam_role.lambda_execution.arn
}

# ============================================================
# CloudWatch 출력
# ============================================================

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group 이름"
  value       = aws_cloudwatch_log_group.lambda.name
}

# ============================================================
# 배포 정보 (CI/CD용)
# ============================================================

output "deployment_info" {
  description = "CI/CD 배포에 필요한 정보"
  value = {
    aws_region      = data.aws_region.current.name
    aws_account_id  = data.aws_caller_identity.current.account_id
    lambda_function = aws_lambda_function.main.function_name
    function_url    = aws_lambda_function_url.main.function_url
    s3_bucket       = aws_s3_bucket.worklog.bucket
    eventbridge     = aws_cloudwatch_event_rule.daily_worklog.name
  }
}
