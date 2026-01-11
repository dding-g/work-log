# CLAUDE.md

Git 커밋을 분석하여 일일 업무일지를 자동 생성하는 Python 기반 서버리스 API.

## 기술 스택

- **Runtime**: Python 3.11
- **Framework**: FastAPI + Pydantic (로컬), Lambda Handler (AWS)
- **Git 분석**: GitHub API (Lambda), GitPython (로컬)
- **LLM**: OpenAI (GPT-4o-mini) / Anthropic (Claude 3.5 Haiku)
- **배포**: AWS Lambda + ZIP 패키지
- **인프라**: Terraform (S3, EventBridge, CloudWatch)
- **CI/CD**: GitHub Actions

## 디렉토리 구조

```
work-log/
├── core/                    # 핵심 비즈니스 로직
│   ├── api.py              # FastAPI 엔드포인트 (로컬 개발용)
│   ├── lambda_handler.py   # AWS Lambda 진입점
│   ├── github_client.py    # GitHub API 클라이언트
│   ├── s3_storage.py       # S3 스토리지 클라이언트
│   ├── slack_notifier.py   # Slack 알림 전송
│   ├── models.py           # Pydantic 데이터 모델
│   ├── git_analyzer.py     # Git 커밋 분석 (로컬용)
│   ├── summarizer.py       # LLM 요약 (OpenAI/Anthropic)
│   └── generator.py        # Markdown 업무일지 생성
├── terraform/               # AWS 인프라 코드
│   ├── main.tf             # Provider 및 기본 설정
│   ├── lambda.tf           # Lambda 함수 + Function URL
│   ├── s3.tf               # S3 버킷 (업무일지 저장)
│   ├── eventbridge.tf      # 일일 스케줄 규칙
│   ├── iam.tf              # IAM 역할 및 정책
│   ├── cloudwatch.tf       # 로그 그룹
│   ├── variables.tf        # 변수 정의
│   └── outputs.tf          # 출력값
├── .github/workflows/
│   └── deploy-lambda.yml   # Lambda ZIP 배포 파이프라인
├── requirements.txt         # 전체 의존성 (로컬 개발용)
└── requirements-lambda.txt  # Lambda 배포용 최소 의존성
```

## 개발 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 서버 실행 (FastAPI)
uvicorn core.api:app --reload --port 8000

# Lambda 핸들러 로컬 테스트
python -m core.lambda_handler
```

## Terraform 명령어

```bash
cd terraform

# 초기화
terraform init

# 변경사항 확인
terraform plan

# 배포
terraform apply

# 상태 확인
terraform show
```

## 환경 변수

```bash
# GitHub API (필수)
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=ddingg
GITHUB_REPO=work-log

# LLM API 키 (둘 중 하나)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# AWS (Lambda에서 자동 설정)
S3_BUCKET_NAME=work-log-worklogs-xxx

# Slack 알림 (선택)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

## 아키텍처

### Lambda 실행 흐름

```
EventBridge (매일 자정 KST)
        ↓
Lambda Handler (core/lambda_handler.py)
        ↓
GitHub API → 커밋 조회 (core/github_client.py)
        ↓
LLM → AI 요약 생성 (core/summarizer.py)
        ↓
Markdown 생성 (core/generator.py)
        ↓
S3 저장 (core/s3_storage.py)
        ↓
Slack 알림 (core/slack_notifier.py)
```

### 로컬 실행 흐름

```
HTTP Request → FastAPI (core/api.py)
        ↓
GitPython → 로컬 커밋 분석 (core/git_analyzer.py)
        ↓
LLM → AI 요약 생성 (core/summarizer.py)
        ↓
Markdown 생성 + 파일 저장 (core/generator.py)
```

## 주요 모델 (core/models.py)

- `CommitInfo`: 커밋 정보 (hash, subject, body, type, stats)
- `CommitType`: 커밋 타입 enum (feat, fix, refactor, docs, test, chore, style, perf, ci, other)
- `CommitStats`: 커밋 통계 (total_commits, files_changed, insertions, deletions)
- `QualityEvaluation`: 품질 평가 (good_points, improvements, score)
- `WorkLog`: 업무일지 데이터 (date, commits, stats, quality, ai_summary)

## 코드 컨벤션

- **커밋**: Conventional Commits (feat, fix, refactor, docs, test, chore)
- **타입 힌트**: 모든 함수에 명시적 타입 지정
- **데이터 모델**: Pydantic BaseModel 사용
- **주석**: 한국어 주석 사용
- **비동기**: async/await 패턴 사용

## 배포

- **인프라**: `terraform apply`로 AWS 리소스 생성
- **코드 배포**: main 브랜치 푸시 시 GitHub Actions → Lambda 업데이트
- **자동 실행**: EventBridge로 매일 KST 자정에 Lambda 트리거
- **수동 실행**: GitHub Actions workflow_dispatch 또는 Lambda 직접 호출

## GitHub Secrets (CI/CD용)

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION (기본: ap-northeast-2)
LAMBDA_FUNCTION_NAME (기본: work-log-api)
```
