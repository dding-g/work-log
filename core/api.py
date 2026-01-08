"""
api.py - FastAPI HTTP 서버 + AWS Lambda 핸들러

이 파일은 HTTP API 서버를 구현합니다.
로컬에서는 uvicorn으로, AWS Lambda에서는 Mangum 어댑터로 실행됩니다.

FastAPI란?
- 파이썬으로 API 서버를 만드는 현대적인 프레임워크
- 자동으로 API 문서(Swagger) 생성
- 빠른 성능 (비동기 지원)
- 타입 힌트 기반 자동 검증

Mangum이란?
- AWS Lambda에서 ASGI 앱(FastAPI)을 실행하게 해주는 어댑터
- Lambda의 이벤트를 HTTP 요청으로 변환
- API Gateway, ALB 등과 연동 가능
"""

# ============================================================
# 임포트
# ============================================================

# 날짜 처리
from datetime import date, timedelta

# 파일 경로
from pathlib import Path

# 타입 힌트
from typing import Optional

# FastAPI 관련
# FastAPI: 앱 인스턴스 생성에 사용
# HTTPException: HTTP 에러 응답을 위한 예외
from fastapi import FastAPI, HTTPException, Query

# CORS: 다른 도메인에서 API 호출을 허용하는 설정
# 브라우저 보안 정책 때문에 필요
from fastapi.middleware.cors import CORSMiddleware

# 정적 파일 서빙 (Markdown 파일 다운로드용)
from fastapi.responses import FileResponse, PlainTextResponse

# 우리가 만든 모듈들
from core.models import (
    GenerateRequest, GenerateResponse,
    WorkLog, CommitStats, QualityEvaluation
)
from core.git_analyzer import GitAnalyzer
from core.generator import MarkdownGenerator
from core.summarizer import get_summarizer


# ============================================================
# FastAPI 앱 생성
# ============================================================

# FastAPI 인스턴스 생성
# 이 객체가 우리 API 서버의 핵심
app = FastAPI(
    title="Work-Log API",                    # API 제목
    description="Git 커밋 기반 업무일지 자동 생성 API",  # 설명
    version="1.0.0",                          # 버전
    docs_url="/docs",                         # Swagger 문서 URL
    redoc_url="/redoc"                        # ReDoc 문서 URL
)

# CORS 설정 추가
# 모든 도메인에서 API 호출을 허용 (개발용)
# 프로덕션에서는 특정 도메인만 허용하는 것이 안전
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 모든 도메인 허용
    allow_credentials=True,       # 쿠키 허용
    allow_methods=["*"],          # 모든 HTTP 메서드 허용
    allow_headers=["*"],          # 모든 헤더 허용
)


# ============================================================
# 헬퍼 함수
# ============================================================

def get_day_of_week(target_date: date) -> str:
    """
    날짜에서 한국어 요일 반환
    """
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return days[target_date.weekday()]


# ============================================================
# API 엔드포인트 정의
# ============================================================

# @app.get(), @app.post() 등은 "데코레이터"
# 데코레이터: 함수에 추가 기능을 부여하는 문법
# 여기서는 "이 함수를 HTTP 엔드포인트로 등록해라"는 의미


@app.get("/")
async def root():
    """
    루트 경로 - API 상태 확인용

    GET /

    이 엔드포인트는 API가 정상 동작하는지 확인할 때 사용합니다.
    브라우저에서 http://localhost:8000/ 접속하면 이 응답을 받습니다.
    """
    return {
        "status": "running",
        "message": "Work-Log API가 실행 중입니다.",
        "docs": "/docs",      # Swagger 문서 링크
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트

    GET /health

    서버가 살아있는지 확인하는 용도입니다.
    모니터링 시스템이나 로드밸런서가 주기적으로 호출합니다.
    """
    return {"status": "healthy"}


@app.post("/generate", response_model=GenerateResponse)
async def generate_worklog(request: GenerateRequest):
    """
    업무일지 생성 API

    POST /generate

    요청 본문(Body)에 JSON으로 옵션을 전달합니다:
    {
        "target_date": "2024-01-15",    // 선택, 기본값=어제
        "repo_path": "/path/to/repo",   // 선택, 기본값=현재 디렉토리
        "use_ai_summary": true          // 선택, 기본값=true
    }

    response_model=GenerateResponse:
    - 응답의 형태를 지정
    - 자동으로 응답 검증 및 문서화
    """
    try:
        # ===== 1. 매개변수 설정 =====

        # 대상 날짜 (없으면 어제)
        target_date = request.target_date
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        # 저장소 경로 (없으면 현재 디렉토리)
        repo_path = request.repo_path or "."

        # ===== 2. Git 분석 =====

        # GitAnalyzer 인스턴스 생성
        try:
            analyzer = GitAnalyzer(repo_path)
        except ValueError as e:
            # Git 저장소가 아닌 경우
            raise HTTPException(
                status_code=400,  # Bad Request
                detail=str(e)
            )

        # 커밋 가져오기
        commits = analyzer.get_commits_for_date(target_date)

        # 통계 계산
        stats = analyzer.calculate_stats(commits)

        # 품질 평가
        quality = analyzer.evaluate_quality(commits)

        # ===== 3. AI 요약 (선택적) =====

        ai_summary = None
        if request.use_ai_summary and commits:
            try:
                # 요약기 가져오기 (auto: 환경변수 기반 자동 선택)
                summarizer = get_summarizer("auto")

                # 비동기로 요약 생성
                # await: 비동기 작업이 끝날 때까지 대기
                ai_summary = await summarizer.summarize(commits)
            except Exception as e:
                # 요약 실패해도 계속 진행
                ai_summary = f"[요약 생성 실패: {str(e)}]"

        # ===== 4. WorkLog 객체 생성 =====

        worklog = WorkLog(
            target_date=target_date,
            day_of_week=get_day_of_week(target_date),
            repository_name=analyzer.get_repo_name(),
            commits=commits,
            stats=stats,
            quality=quality,
            ai_summary=ai_summary
        )

        # ===== 5. Markdown 파일 저장 =====

        generator = MarkdownGenerator("./worklog")
        saved_path = generator.save(worklog)

        # ===== 6. 응답 반환 =====

        return GenerateResponse(
            success=True,
            worklog=worklog,
            markdown_path=str(saved_path)
        )

    except HTTPException:
        # HTTPException은 그대로 다시 발생
        raise
    except Exception as e:
        # 기타 예외는 500 에러로 변환
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail=f"업무일지 생성 중 오류: {str(e)}"
        )


@app.get("/generate/quick")
async def generate_worklog_quick(
    target_date: Optional[date] = Query(
        default=None,
        description="대상 날짜 (YYYY-MM-DD 형식, 기본값: 어제)"
    ),
    repo_path: Optional[str] = Query(
        default=None,
        description="Git 저장소 경로 (기본값: 현재 디렉토리)"
    ),
    use_ai: bool = Query(
        default=True,
        description="AI 요약 사용 여부"
    )
):
    """
    GET 방식 업무일지 생성 (간편 호출용)

    GET /generate/quick?target_date=2024-01-15&use_ai=true

    Query 매개변수:
    - target_date: 대상 날짜
    - repo_path: 저장소 경로
    - use_ai: AI 요약 사용 여부

    Query(): FastAPI에서 쿼리 파라미터를 정의할 때 사용
    - URL의 ? 뒤에 오는 파라미터들
    - 예: /generate/quick?target_date=2024-01-15
    """
    # POST 엔드포인트 재사용
    request = GenerateRequest(
        target_date=target_date,
        repo_path=repo_path,
        use_ai_summary=use_ai
    )
    return await generate_worklog(request)


@app.get("/worklog/{file_date}")
async def get_worklog(file_date: str):
    """
    저장된 업무일지 조회

    GET /worklog/2024-01-15

    경로 매개변수:
    - file_date: 조회할 날짜 (YYYY-MM-DD 형식)

    {file_date}는 "경로 매개변수(path parameter)"
    URL 경로의 일부로 값을 전달받습니다.
    """
    # 파일 경로 생성
    file_path = Path(f"./worklog/{file_date}.md")

    # 파일 존재 확인
    if not file_path.exists():
        raise HTTPException(
            status_code=404,  # Not Found
            detail=f"{file_date} 날짜의 업무일지를 찾을 수 없습니다."
        )

    # 파일 내용 읽기
    content = file_path.read_text(encoding="utf-8")

    # PlainTextResponse: 일반 텍스트로 응답
    # media_type: Content-Type 헤더 설정
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8"
    )


@app.get("/worklog/{file_date}/download")
async def download_worklog(file_date: str):
    """
    업무일지 파일 다운로드

    GET /worklog/2024-01-15/download

    브라우저에서 호출하면 파일이 다운로드됩니다.
    """
    file_path = Path(f"./worklog/{file_date}.md")

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{file_date} 날짜의 업무일지를 찾을 수 없습니다."
        )

    # FileResponse: 파일을 응답으로 전송
    # filename: 다운로드될 때의 파일 이름
    return FileResponse(
        path=file_path,
        filename=f"worklog-{file_date}.md",
        media_type="text/markdown"
    )


@app.get("/worklogs")
async def list_worklogs():
    """
    저장된 모든 업무일지 목록 조회

    GET /worklogs

    worklog 디렉토리에 있는 모든 .md 파일 목록을 반환합니다.
    """
    worklog_dir = Path("./worklog")

    # 디렉토리가 없으면 빈 목록 반환
    if not worklog_dir.exists():
        return {"worklogs": []}

    # .md 파일 목록 가져오기
    # glob("*.md"): 패턴과 일치하는 파일 찾기
    md_files = list(worklog_dir.glob("*.md"))

    # 날짜순 정렬 (최신순)
    # sorted(): 정렬된 새 리스트 반환
    # key=lambda f: f.stem: 파일 이름(확장자 제외)으로 정렬
    # reverse=True: 내림차순 (최신이 먼저)
    md_files = sorted(md_files, key=lambda f: f.stem, reverse=True)

    # 결과 생성
    worklogs = []
    for f in md_files:
        worklogs.append({
            "date": f.stem,                    # 파일 이름 (확장자 제외)
            "path": str(f),                    # 전체 경로
            "url": f"/worklog/{f.stem}",       # API URL
            "download_url": f"/worklog/{f.stem}/download"
        })

    return {"worklogs": worklogs, "count": len(worklogs)}


# ============================================================
# AWS Lambda 핸들러
# ============================================================

# Mangum: FastAPI를 AWS Lambda에서 실행하게 해주는 어댑터
# Lambda가 받은 이벤트를 HTTP 요청으로 변환해서 FastAPI에 전달
try:
    from mangum import Mangum

    # Lambda 핸들러 생성
    # 이 handler를 Lambda 함수의 진입점으로 설정
    # Lambda 설정: Handler = core.api.handler
    handler = Mangum(
        app,
        lifespan="off",  # Lambda는 수명주기 이벤트 불필요
        api_gateway_base_path=None  # API Gateway 기본 경로 (필요시 설정)
    )

except ImportError:
    # Mangum이 없으면 (로컬 개발 환경)
    # handler를 None으로 설정
    handler = None


# ============================================================
# 로컬 서버 실행
# ============================================================

# 이 파일을 직접 실행할 때 서버 시작
if __name__ == "__main__":
    # uvicorn: ASGI 서버 (비동기 웹 서버)
    # FastAPI 앱을 실행하는 데 사용
    import uvicorn

    print("=" * 50)
    print("Work-Log API 서버 시작")
    print("=" * 50)
    print("- API 문서: http://localhost:8000/docs")
    print("- 대체 문서: http://localhost:8000/redoc")
    print("=" * 50)

    # 서버 실행
    uvicorn.run(
        "core.api:app",          # 앱 위치 (모듈:객체)
        host="0.0.0.0",          # 모든 IP에서 접속 허용
        port=8000,               # 포트 번호
        reload=True              # 코드 변경 시 자동 재시작 (개발용)
    )
