# ============================================================
# Terraform 설정
# ============================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # 선택: S3 백엔드 (상태 파일 원격 저장)
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "work-log/terraform.tfstate"
  #   region = "ap-northeast-2"
  # }
}

# ============================================================
# AWS Provider
# ============================================================

provider "aws" {
  region = var.aws_region
  # AWS 자격 증명은 환경변수(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)에서 자동 로드

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

# ============================================================
# Data Sources
# ============================================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}
