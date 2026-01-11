# ============================================================
# S3 버킷 (업무일지 저장용)
# ============================================================

resource "aws_s3_bucket" "worklog" {
  bucket = "${var.project_name}-worklogs-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-worklog-bucket"
  }
}

# ============================================================
# S3 버킷 버전 관리
# ============================================================

resource "aws_s3_bucket_versioning" "worklog" {
  bucket = aws_s3_bucket.worklog.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================================
# S3 버킷 암호화
# ============================================================

resource "aws_s3_bucket_server_side_encryption_configuration" "worklog" {
  bucket = aws_s3_bucket.worklog.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ============================================================
# S3 버킷 퍼블릭 액세스 차단
# ============================================================

resource "aws_s3_bucket_public_access_block" "worklog" {
  bucket = aws_s3_bucket.worklog.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================
# S3 버킷 수명 주기 정책 (오래된 파일 자동 삭제)
# ============================================================

resource "aws_s3_bucket_lifecycle_configuration" "worklog" {
  bucket = aws_s3_bucket.worklog.id

  rule {
    id     = "expire-old-worklogs"
    status = "Enabled"

    # 모든 객체에 적용
    filter {
      prefix = ""
    }

    # 365일 후 삭제
    expiration {
      days = 365
    }

    # 이전 버전은 90일 후 삭제
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
