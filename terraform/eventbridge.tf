# ============================================================
# EventBridge 스케줄 규칙 (매일 자정 KST)
# ============================================================

resource "aws_cloudwatch_event_rule" "daily_worklog" {
  name                = "${var.project_name}-daily-schedule"
  description         = "매일 자정(KST)에 업무일지 생성 Lambda 트리거"
  schedule_expression = "cron(0 15 * * ? *)"  # UTC 15:00 = KST 00:00

  tags = {
    Name = "${var.project_name}-eventbridge-rule"
  }
}

# ============================================================
# EventBridge 타겟 (Lambda 함수)
# ============================================================

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_worklog.name
  target_id = "DailyWorklogLambda"
  arn       = aws_lambda_function.main.arn
}

# ============================================================
# Lambda 퍼미션 (EventBridge에서 호출 허용)
# ============================================================

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_worklog.arn
}
