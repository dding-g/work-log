# ============================================================
# AWS 설정
# ============================================================

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

# ============================================================
# 프로젝트 설정
# ============================================================

variable "project_name" {
  description = "프로젝트 이름 (리소스 네이밍에 사용)"
  type        = string
  default     = "work-log"
}

variable "function_name" {
  description = "Lambda 함수 이름"
  type        = string
  default     = "work-log-api"
}

# ============================================================
# Lambda 설정
# ============================================================

variable "lambda_memory_size" {
  description = "Lambda 메모리 크기 (MB)"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda 타임아웃 (초)"
  type        = number
  default     = 30
}

variable "lambda_architecture" {
  description = "Lambda 아키텍처 (x86_64 또는 arm64)"
  type        = string
  default     = "x86_64"
}

# ============================================================
# 환경 변수 (민감정보)
# ============================================================

variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API Key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub 저장소 소유자"
  type        = string
  default     = "ddingg"
}

variable "github_repo" {
  description = "GitHub 저장소 이름"
  type        = string
  default     = "work-log"
}

variable "slack_webhook_url" {
  description = "Slack Webhook URL"
  type        = string
  default     = ""
  sensitive   = true
}

# ============================================================
# CloudWatch 설정
# ============================================================

variable "log_retention_days" {
  description = "CloudWatch 로그 보관 기간 (일)"
  type        = number
  default     = 14
}
