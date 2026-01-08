# Work-Log Automation 📝

Git 커밋을 분석하여 일일 업무일지를 자동 생성하는 서버리스 API입니다.

## 기능

- **Git 커밋 분석**: 특정 날짜의 커밋을 자동 수집
- **타입별 분류**: feat, fix, refactor 등 커밋 컨벤션 자동 인식
- **AI 요약**: OpenAI GPT 또는 Anthropic Claude로 커밋 내용 요약
- **품질 평가**: 커밋 크기, 메시지 품질 자동 분석
- **AWS Lambda**: 서버리스로 운영 비용 절감
- **HTTP API**: n8n, Slack 등 외부 서비스와 쉬운 연동

## 아키텍처

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  GitHub     │     │   Lambda    │     │   Slack     │
│  Actions    │────▶│   (API)     │────▶│   Webhook   │
│  (Cron)     │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │    ECR      │
                    │  (Docker)   │
                    └─────────────┘
```

## 프로젝트 구조

```
work-log/
├── core/                       # 핵심 로직
│   ├── api.py                  # FastAPI + Lambda 핸들러
│   ├── models.py               # 데이터 모델 (Pydantic)
│   ├── git_analyzer.py         # Git 커밋 분석
│   ├── summarizer.py           # AI 요약 (OpenAI/Claude)
│   └── generator.py            # Markdown 생성
├── Dockerfile                  # Lambda 컨테이너 이미지
├── requirements.txt            # Python 의존성
└── .github/workflows/
    ├── deploy-lambda.yml       # ECR/Lambda 배포
    └── daily-worklog.yml       # 일일 업무일지 생성
```

## 빠른 시작

### 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 서버 실행
python -m core.api

# API 문서: http://localhost:8000/docs
```

### Docker 로컬 테스트

```bash
# 이미지 빌드
docker build -t work-log-lambda .

# 컨테이너 실행
docker run -p 9000:8080 work-log-lambda

# Lambda 형식으로 테스트
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"httpMethod": "GET", "path": "/health"}'
```

## AWS Lambda 배포

### 1. 사전 준비

```bash
# ECR 저장소 생성
aws ecr create-repository --repository-name work-log-api

# Lambda 함수 생성 (컨테이너 이미지 기반)
aws lambda create-function \
  --function-name work-log-api \
  --package-type Image \
  --code ImageUri=<ECR_URI>:latest \
  --role arn:aws:iam::<ACCOUNT_ID>:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 512
```

### 2. GitHub Secrets 설정

| Secret | 설명 |
|--------|------|
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키 |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 키 |
| `AWS_REGION` | AWS 리전 (예: ap-northeast-2) |
| `ECR_REPOSITORY` | ECR 저장소 이름 |
| `LAMBDA_FUNCTION_NAME` | Lambda 함수 이름 |
| `LAMBDA_FUNCTION_URL` | Lambda Function URL |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL (선택) |
| `OPENAI_API_KEY` | OpenAI API 키 (선택) |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (선택) |

### 3. 배포

main 브랜치에 푸시하면 자동으로 배포됩니다:

```bash
git push origin main
```

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | API 상태 확인 |
| GET | `/health` | 헬스 체크 |
| POST | `/generate` | 업무일지 생성 |
| GET | `/generate/quick` | 간편 생성 |
| GET | `/worklog/{date}` | 업무일지 조회 |
| GET | `/worklogs` | 목록 조회 |

### 업무일지 생성 예시

```bash
# Lambda Function URL 사용
curl -X POST "https://xxx.lambda-url.ap-northeast-2.on.aws/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "target_date": "2024-01-15",
    "use_ai_summary": true
  }'
```

## GitHub Actions 워크플로우

### deploy-lambda.yml

main 브랜치 푸시 시 자동 실행:
1. Docker 이미지 빌드
2. ECR에 푸시
3. Lambda 함수 업데이트

### daily-worklog.yml

매일 오전 9시(KST) 실행:
1. Lambda API 호출
2. 업무일지 생성
3. Slack으로 결과 전송

## 파일별 설명

| 파일 | 역할 | 주요 개념 |
|------|------|----------|
| `api.py` | HTTP API + Lambda 핸들러 | FastAPI, Mangum |
| `models.py` | 데이터 구조 정의 | Pydantic, 타입 힌트 |
| `git_analyzer.py` | Git 커밋 분석 | GitPython |
| `summarizer.py` | AI 요약 | async/await, OpenAI/Claude |
| `generator.py` | Markdown 생성 | 문자열 처리 |

## n8n 연동

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Cron 트리거  │ ──▶ │ HTTP Request     │ ──▶ │ Slack 노드  │
│ (매일 09:00) │     │ POST /generate   │     │ 결과 전송   │
└─────────────┘     └──────────────────┘     └─────────────┘
```

- **URL**: `https://xxx.lambda-url.xxx.on.aws/generate`
- **Method**: POST
- **Body**: `{"use_ai_summary": true}`

## 라이선스

MIT License
