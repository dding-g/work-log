"""
core 패키지

이 파일(__init__.py)은 이 디렉토리가 파이썬 "패키지"임을 알려줍니다.
패키지란 관련 모듈들을 묶어놓은 폴더입니다.

이 파일이 있으면:
- from core import models 처럼 임포트 가능
- from core.models import CommitInfo 처럼 사용 가능
"""

# 버전 정보
__version__ = "1.0.0"

# 패키지에서 바로 임포트할 수 있게 노출
# from core import GitAnalyzer 처럼 사용 가능
from core.models import (
    CommitType,
    CommitInfo,
    CommitStats,
    QualityEvaluation,
    WorkLog,
    GenerateRequest,
    GenerateResponse
)
from core.generator import MarkdownGenerator
from core.summarizer import (
    BaseSummarizer,
    OpenAISummarizer,
    AnthropicSummarizer,
    FallbackSummarizer,
    get_summarizer
)

# GitAnalyzer는 로컬 환경에서만 사용 (GitPython 필요)
# Lambda 환경에서는 github_client.py 사용
try:
    from core.git_analyzer import GitAnalyzer
except ImportError:
    GitAnalyzer = None  # Lambda 환경에서는 사용 불가
