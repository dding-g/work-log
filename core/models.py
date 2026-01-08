"""
models.py - 데이터 모델 정의

이 파일은 우리 프로그램에서 사용할 "데이터의 형태"를 정의합니다.
마치 엑셀에서 열(column)을 미리 정해두는 것과 비슷해요.

Pydantic이라는 라이브러리를 사용하는데, 이건:
1. 데이터 검증 (잘못된 데이터가 들어오면 에러)
2. 자동 변환 (문자열 "123"을 숫자 123으로)
3. API 문서 자동 생성
을 해줍니다.
"""

# ============================================================
# 임포트 (import) - 다른 파일에서 기능을 가져오기
# ============================================================

# datetime: 날짜와 시간을 다루는 파이썬 기본 라이브러리
# date는 날짜(2024-01-15), datetime은 날짜+시간(2024-01-15 14:30:00)
from datetime import date, datetime

# List, Optional: 타입 힌트를 위한 도구
# List[str]은 "문자열의 리스트"라는 뜻 (예: ["a", "b", "c"])
# Optional[str]은 "문자열이거나 None일 수 있다"는 뜻
from typing import List, Optional

# Pydantic의 BaseModel: 모든 데이터 모델의 부모 클래스
# Field: 각 필드에 추가 정보(기본값, 설명 등)를 넣을 때 사용
from pydantic import BaseModel, Field

# Enum: 정해진 값들 중 하나만 선택할 수 있게 하는 도구
# 예: 커밋 타입은 "feat", "fix", "refactor" 중 하나
from enum import Enum


# ============================================================
# 열거형 (Enum) - 정해진 선택지 정의
# ============================================================

class CommitType(str, Enum):
    """
    커밋 타입을 정의하는 열거형 (Enum)

    Git 커밋 메시지의 컨벤션(관례)에 따른 타입들입니다.
    예: "feat: 로그인 기능 추가" → CommitType.FEAT

    str을 상속받은 이유: JSON으로 변환할 때 "feat" 같은 문자열로 나오게 하려고
    """

    FEAT = "feat"           # 새로운 기능 추가
    FIX = "fix"             # 버그 수정
    REFACTOR = "refactor"   # 코드 리팩토링 (기능 변화 없이 코드 개선)
    DOCS = "docs"           # 문서 수정
    TEST = "test"           # 테스트 코드 추가/수정
    CHORE = "chore"         # 빌드, 설정 등 기타 작업
    STYLE = "style"         # 코드 스타일 변경 (포맷팅 등)
    PERF = "perf"           # 성능 개선
    CI = "ci"               # CI/CD 관련 변경
    OTHER = "other"         # 위에 해당 안 되는 것들


# ============================================================
# 데이터 모델 (Data Models) - 데이터 구조 정의
# ============================================================

class CommitInfo(BaseModel):
    """
    하나의 Git 커밋 정보를 담는 모델

    Git에서 가져온 커밋 하나의 정보를 저장합니다.

    사용 예시:
        commit = CommitInfo(
            hash="abc1234",
            subject="feat: 로그인 기능 추가",
            body="상세 설명...",
            author_email="dev@example.com",
            timestamp=datetime.now()
        )
    """

    # 커밋 해시: Git이 각 커밋에 부여하는 고유 ID (예: "abc1234")
    # Field()를 사용하면 추가 정보를 넣을 수 있어요
    hash: str = Field(
        ...,  # ...은 "필수값"이라는 뜻 (반드시 있어야 함)
        description="커밋의 고유 해시값 (짧은 형태)",
        example="abc1234"
    )

    # 커밋 제목: 커밋 메시지의 첫 줄
    subject: str = Field(
        ...,
        description="커밋 메시지의 제목 (첫 줄)",
        example="feat: 사용자 인증 기능 추가"
    )

    # 커밋 본문: 제목 아래의 상세 설명 (없을 수도 있음)
    # Optional[str]은 str 또는 None이 될 수 있다는 뜻
    body: Optional[str] = Field(
        default=None,  # 기본값은 None (없음)
        description="커밋 메시지의 본문 (상세 설명)"
    )

    # 작성자 이메일
    author_email: str = Field(
        ...,
        description="커밋 작성자의 이메일"
    )

    # 커밋 시각
    timestamp: datetime = Field(
        ...,
        description="커밋이 생성된 시각"
    )

    # 커밋 타입: 위에서 정의한 CommitType 중 하나
    commit_type: CommitType = Field(
        default=CommitType.OTHER,
        description="커밋의 타입 (feat, fix 등)"
    )

    # 변경된 파일 목록
    # List[str]은 문자열의 리스트라는 뜻 (예: ["file1.py", "file2.py"])
    changed_files: List[str] = Field(
        default_factory=list,  # 기본값으로 빈 리스트 [] 생성
        description="이 커밋에서 변경된 파일 목록"
    )

    # 추가된 라인 수
    insertions: int = Field(
        default=0,
        description="추가된 코드 라인 수"
    )

    # 삭제된 라인 수
    deletions: int = Field(
        default=0,
        description="삭제된 코드 라인 수"
    )


class CommitStats(BaseModel):
    """
    커밋 통계 정보를 담는 모델

    하루 동안의 전체 커밋 통계를 요약합니다.
    """

    total_commits: int = Field(
        default=0,
        description="총 커밋 수"
    )

    total_files_changed: int = Field(
        default=0,
        description="변경된 파일 총 수"
    )

    total_insertions: int = Field(
        default=0,
        description="추가된 라인 총 수"
    )

    total_deletions: int = Field(
        default=0,
        description="삭제된 라인 총 수"
    )

    # 타입별 커밋 수를 딕셔너리로 저장
    # 예: {"feat": 3, "fix": 2, "refactor": 1}
    commits_by_type: dict = Field(
        default_factory=dict,
        description="커밋 타입별 개수"
    )


class QualityEvaluation(BaseModel):
    """
    코드 품질 평가 결과를 담는 모델

    커밋들을 분석해서 잘한 점과 개선할 점을 저장합니다.
    """

    # 잘한 점 목록
    good_points: List[str] = Field(
        default_factory=list,
        description="잘한 점 목록"
    )

    # 개선할 점 목록
    improvements: List[str] = Field(
        default_factory=list,
        description="개선이 필요한 점 목록"
    )

    # 전체 점수 (0~100)
    score: int = Field(
        default=0,
        ge=0,   # ge = greater than or equal (0 이상)
        le=100, # le = less than or equal (100 이하)
        description="전체 품질 점수 (0-100)"
    )


class WorkLog(BaseModel):
    """
    최종 업무일지를 담는 모델

    이게 우리가 최종적으로 만들어내는 업무일지의 형태입니다.
    API 응답으로도 사용되고, Markdown 생성의 기반이 됩니다.
    """

    # 대상 날짜
    target_date: date = Field(
        ...,
        description="업무일지 대상 날짜"
    )

    # 요일 (월요일, 화요일 등)
    day_of_week: str = Field(
        ...,
        description="요일"
    )

    # 저장소 이름
    repository_name: str = Field(
        ...,
        description="Git 저장소 이름"
    )

    # 커밋 목록
    commits: List[CommitInfo] = Field(
        default_factory=list,
        description="해당 날짜의 모든 커밋"
    )

    # 통계 정보
    stats: CommitStats = Field(
        default_factory=CommitStats,
        description="커밋 통계"
    )

    # 품질 평가
    quality: QualityEvaluation = Field(
        default_factory=QualityEvaluation,
        description="품질 평가 결과"
    )

    # AI가 생성한 요약 (선택적)
    ai_summary: Optional[str] = Field(
        default=None,
        description="AI가 생성한 업무 요약"
    )

    # 생성 시각
    generated_at: datetime = Field(
        default_factory=datetime.now,  # 기본값: 현재 시각
        description="업무일지가 생성된 시각"
    )


# ============================================================
# API 요청/응답 모델 - HTTP API에서 사용
# ============================================================

class GenerateRequest(BaseModel):
    """
    업무일지 생성 API 요청 모델

    클라이언트가 POST /generate 로 보내는 데이터의 형태
    """

    # 대상 날짜 (없으면 어제)
    target_date: Optional[date] = Field(
        default=None,
        description="업무일지를 생성할 날짜 (기본값: 어제)"
    )

    # 저장소 경로 (없으면 현재 디렉토리)
    repo_path: Optional[str] = Field(
        default=None,
        description="Git 저장소 경로 (기본값: 현재 디렉토리)"
    )

    # AI 요약 사용 여부
    use_ai_summary: bool = Field(
        default=True,
        description="AI 요약 기능 사용 여부"
    )


class GenerateResponse(BaseModel):
    """
    업무일지 생성 API 응답 모델
    """

    # 성공 여부
    success: bool = Field(
        ...,
        description="생성 성공 여부"
    )

    # 에러 메시지 (실패 시)
    error: Optional[str] = Field(
        default=None,
        description="에러 메시지 (실패 시)"
    )

    # 생성된 업무일지
    worklog: Optional[WorkLog] = Field(
        default=None,
        description="생성된 업무일지"
    )

    # 생성된 Markdown 파일 경로
    markdown_path: Optional[str] = Field(
        default=None,
        description="저장된 Markdown 파일 경로"
    )
