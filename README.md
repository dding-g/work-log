# Work-Log Automation 📝

Git 커밋을 분석하여 일일 업무일지를 자동 생성하는 Python API 서버입니다.

## 기능

- **Git 커밋 분석**: 특정 날짜의 커밋을 자동 수집
- **타입별 분류**: feat, fix, refactor 등 커밋 컨벤션 자동 인식
- **AI 요약**: OpenAI GPT 또는 Anthropic Claude로 커밋 내용 요약
- **품질 평가**: 커밋 크기, 메시지 품질 자동 분석
- **HTTP API**: n8n, Slack 등 외부 서비스와 쉬운 연동

## 프로젝트 구조

```
work-log/
├── core/                    # 핵심 로직
│   ├── __init__.py         # 패키지 초기화
│   ├── models.py           # 데이터 모델 (Pydantic)
│   ├── git_analyzer.py     # Git 커밋 분석
│   ├── summarizer.py       # AI 요약 (OpenAI/Claude)
│   ├── generator.py        # Markdown 생성
│   └── api.py              # FastAPI 서버
├── worklog/                 # 생성된 업무일지
├── config/                  # 설정 파일
├── .env.example            # 환경변수 템플릿
├── requirements.txt        # Python 의존성
└── README.md
```

## 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd work-log

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# LLM 사용 시 추가 설치
pip install openai      # GPT 사용 시
pip install anthropic   # Claude 사용 시
```

### 2. 환경 설정

```bash
# 환경변수 파일 생성
cp .env.example .env

# .env 파일 편집하여 API 키 설정
```

### 3. 서버 실행

```bash
# 방법 1: Python으로 직접 실행
python -m core.api

# 방법 2: uvicorn으로 실행
uvicorn core.api:app --reload --host 0.0.0.0 --port 8000
```

서버가 시작되면:
- API 문서: http://localhost:8000/docs
- 대체 문서: http://localhost:8000/redoc

## API 사용법

### 업무일지 생성

```bash
# POST 방식 (상세 옵션)
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "target_date": "2024-01-15",
    "use_ai_summary": true
  }'

# GET 방식 (간편)
curl "http://localhost:8000/generate/quick?target_date=2024-01-15"
```

### 업무일지 조회

```bash
# 특정 날짜 업무일지 조회
curl http://localhost:8000/worklog/2024-01-15

# 모든 업무일지 목록
curl http://localhost:8000/worklogs

# 파일 다운로드
curl -O http://localhost:8000/worklog/2024-01-15/download
```

## n8n 연동

n8n에서 HTTP Request 노드로 연동할 수 있습니다:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Cron 트리거  │ ──▶ │ HTTP Request │ ──▶ │ Slack 노드  │
│ (매일 02:00) │     │ POST /generate│     │ 결과 전송   │
└─────────────┘     └──────────────┘     └─────────────┘
```

### n8n HTTP Request 설정

- **Method**: POST
- **URL**: http://localhost:8000/generate
- **Body Type**: JSON
- **Body**:
  ```json
  {
    "use_ai_summary": true
  }
  ```

## 파일별 설명

| 파일 | 역할 | 주요 개념 |
|------|------|----------|
| `models.py` | 데이터 구조 정의 | Pydantic, 타입 힌트, Enum |
| `git_analyzer.py` | Git 커밋 분석 | GitPython, 클래스 |
| `summarizer.py` | AI 요약 | 비동기(async/await), 추상 클래스 |
| `generator.py` | Markdown 생성 | 문자열 처리, Path |
| `api.py` | HTTP API | FastAPI, 데코레이터 |

## 코드 구조 가이드 (초보자용)

### 1. 클래스와 객체

```python
# 클래스: 설계도
class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        print(f"{self.name}가 짖습니다!")

# 객체: 설계도로 만든 실제 인스턴스
my_dog = Dog("멍멍이")
my_dog.bark()  # "멍멍이가 짖습니다!"
```

### 2. 타입 힌트

```python
# 함수의 입력과 출력 타입을 명시
def greet(name: str) -> str:
    return f"안녕하세요, {name}!"

# 리스트, 옵션 타입
from typing import List, Optional

def process(items: List[str], count: Optional[int] = None) -> None:
    pass
```

### 3. 비동기 프로그래밍

```python
import asyncio

# async: 비동기 함수 선언
async def fetch_data():
    await asyncio.sleep(1)  # await: 비동기 작업 대기
    return "데이터"

# 실행
result = asyncio.run(fetch_data())
```

## 라이선스

MIT License
