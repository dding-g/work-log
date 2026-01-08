"""
summarizer.py - LLM 기반 커밋 요약기

이 파일은 AI(LLM)를 사용해서 커밋 내용을 자연스러운 문장으로 요약합니다.
OpenAI(GPT)와 Anthropic(Claude) 두 가지 API를 지원합니다.

LLM이란?
- Large Language Model의 약자
- ChatGPT, Claude 같은 대화형 AI 모델
- 텍스트를 이해하고 생성할 수 있음
"""

# ============================================================
# 임포트
# ============================================================

# 비동기 프로그래밍을 위한 모듈
# async/await: 여러 작업을 동시에 처리할 수 있게 해줌
# API 호출 같은 I/O 작업에 특히 유용
import asyncio

# 환경변수를 읽기 위한 모듈
import os

# 타입 힌트
from typing import List, Optional

# ABC: Abstract Base Class (추상 기본 클래스)
# 여러 LLM 제공자(OpenAI, Anthropic)의 공통 인터페이스를 정의
from abc import ABC, abstractmethod

# 우리가 만든 모델
from core.models import CommitInfo


# ============================================================
# 추상 기본 클래스 - 모든 요약기의 공통 인터페이스
# ============================================================

class BaseSummarizer(ABC):
    """
    모든 LLM 요약기의 부모 클래스 (추상 클래스)

    추상 클래스란?
    - 직접 객체를 만들 수 없고, 상속해서만 사용 가능
    - 자식 클래스가 반드시 구현해야 할 메서드를 정의
    - 마치 "설계 계약서"와 같음

    왜 사용하나?
    - OpenAI든 Anthropic이든 같은 방식으로 사용 가능
    - 나중에 다른 LLM 추가도 쉬움
    """

    @abstractmethod  # 이 메서드는 자식 클래스에서 반드시 구현해야 함
    async def summarize(self, commits: List[CommitInfo]) -> str:
        """
        커밋 목록을 요약하는 메서드 (자식 클래스에서 구현)

        async: 비동기 메서드임을 나타냄
        """
        pass  # 구현 없음 (자식 클래스에서 구현)


# ============================================================
# OpenAI (GPT) 요약기
# ============================================================

class OpenAISummarizer(BaseSummarizer):
    """
    OpenAI GPT를 사용한 요약기

    GPT-4 또는 GPT-3.5-turbo 모델을 사용합니다.
    API 키는 환경변수 OPENAI_API_KEY에서 읽습니다.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"  # 가장 비용 효율적인 모델
    ):
        """
        생성자

        매개변수:
            api_key: OpenAI API 키 (없으면 환경변수에서 읽음)
            model: 사용할 모델 이름
        """
        # API 키 설정
        # or: 왼쪽이 None/빈문자열이면 오른쪽 값 사용
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        # API 키 확인
        if not self.api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. "
                "OPENAI_API_KEY 환경변수를 설정하거나 api_key 매개변수를 전달하세요."
            )

    def _build_prompt(self, commits: List[CommitInfo]) -> str:
        """
        LLM에게 보낼 프롬프트(질문) 생성

        프롬프트 엔지니어링:
        - LLM에게 원하는 결과를 얻기 위해 질문을 잘 구성하는 것
        - 명확한 지시와 예시가 중요
        """
        # 커밋 목록을 텍스트로 변환
        commits_text = "\n".join([
            f"- [{c.commit_type.value}] {c.subject} "
            f"(+{c.insertions}/-{c.deletions} lines, {len(c.changed_files)} files)"
            for c in commits
        ])

        # 프롬프트 구성
        # 삼중 따옴표(""")로 여러 줄 문자열 작성
        prompt = f"""다음은 오늘 수행한 Git 커밋 목록입니다.
이 커밋들을 분석하여 비즈니스 관점에서 이해하기 쉽게 요약해주세요.

## 커밋 목록
{commits_text}

## 요청사항
1. 기술적인 용어보다는 "무엇을 왜 했는지" 관점으로 작성
2. 3-5개의 핵심 항목으로 요약
3. 각 항목은 한 문장으로 간결하게
4. 한글로 작성
5. 이모지 사용 가능

## 출력 형식
- 첫 번째 작업 내용
- 두 번째 작업 내용
- ...
"""
        return prompt

    async def summarize(self, commits: List[CommitInfo]) -> str:
        """
        커밋 목록을 GPT로 요약

        async/await 설명:
        - async def: 이 함수는 비동기 함수입니다
        - await: 비동기 작업이 끝날 때까지 기다림
        - 비동기를 사용하면 API 응답을 기다리는 동안 다른 일 가능
        """
        # 커밋이 없으면 빈 문자열 반환
        if not commits:
            return "오늘은 커밋이 없습니다."

        # OpenAI 라이브러리 임포트 (런타임에 로드)
        # 이렇게 하면 라이브러리가 없어도 다른 기능은 사용 가능
        try:
            from openai import AsyncOpenAI
        except ImportError:
            return "[OpenAI 라이브러리가 설치되지 않았습니다. pip install openai]"

        # 비동기 클라이언트 생성
        client = AsyncOpenAI(api_key=self.api_key)

        # 프롬프트 생성
        prompt = self._build_prompt(commits)

        try:
            # GPT API 호출
            # await: API 응답을 기다림
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",  # 시스템 메시지: AI의 역할 정의
                        "content": "당신은 개발팀의 업무일지를 작성하는 어시스턴트입니다."
                    },
                    {
                        "role": "user",  # 사용자 메시지: 실제 요청
                        "content": prompt
                    }
                ],
                temperature=0.7,  # 창의성 수준 (0=보수적, 1=창의적)
                max_tokens=1000   # 최대 응답 길이
            )

            # 응답에서 텍스트 추출
            # choices[0]: 첫 번째 응답 선택
            # message.content: 메시지 내용
            return response.choices[0].message.content

        except Exception as e:
            # 에러 발생 시 에러 메시지 반환
            return f"[요약 생성 중 오류 발생: {str(e)}]"


# ============================================================
# Anthropic (Claude) 요약기
# ============================================================

class AnthropicSummarizer(BaseSummarizer):
    """
    Anthropic Claude를 사용한 요약기

    Claude 3.5 Sonnet 또는 Haiku 모델을 사용합니다.
    API 키는 환경변수 ANTHROPIC_API_KEY에서 읽습니다.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-haiku-latest"  # 빠르고 저렴한 모델
    ):
        """
        생성자
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError(
                "Anthropic API 키가 필요합니다. "
                "ANTHROPIC_API_KEY 환경변수를 설정하거나 api_key 매개변수를 전달하세요."
            )

    def _build_prompt(self, commits: List[CommitInfo]) -> str:
        """
        Claude용 프롬프트 생성
        """
        commits_text = "\n".join([
            f"- [{c.commit_type.value}] {c.subject} "
            f"(+{c.insertions}/-{c.deletions} lines)"
            for c in commits
        ])

        return f"""오늘 수행한 Git 커밋들을 분석하여 업무 요약을 작성해주세요.

<commits>
{commits_text}
</commits>

작성 가이드:
- 비즈니스 관점에서 이해하기 쉽게
- 3-5개의 핵심 항목으로 요약
- 각 항목은 한 문장으로 간결하게
- 한글로 작성

출력 형식:
- 첫 번째 작업
- 두 번째 작업
..."""

    async def summarize(self, commits: List[CommitInfo]) -> str:
        """
        커밋 목록을 Claude로 요약
        """
        if not commits:
            return "오늘은 커밋이 없습니다."

        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            return "[Anthropic 라이브러리가 설치되지 않았습니다. pip install anthropic]"

        client = AsyncAnthropic(api_key=self.api_key)
        prompt = self._build_prompt(commits)

        try:
            # Claude API 호출
            response = await client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Claude 응답 구조에서 텍스트 추출
            # content[0].text: 첫 번째 컨텐츠 블록의 텍스트
            return response.content[0].text

        except Exception as e:
            return f"[요약 생성 중 오류 발생: {str(e)}]"


# ============================================================
# 폴백 요약기 (API 없이 동작)
# ============================================================

class FallbackSummarizer(BaseSummarizer):
    """
    API 없이 동작하는 간단한 요약기

    LLM API가 없을 때 사용하는 대안입니다.
    단순히 커밋 메시지를 정리해서 보여줍니다.
    """

    async def summarize(self, commits: List[CommitInfo]) -> str:
        """
        커밋 목록을 단순 정리
        """
        if not commits:
            return "오늘은 커밋이 없습니다."

        # 타입별로 그룹화
        # 딕셔너리 컴프리헨션과 리스트 컴프리헨션 사용
        by_type = {}
        for commit in commits:
            type_name = commit.commit_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(commit.subject)

        # 결과 문자열 생성
        lines = ["## 오늘의 작업 요약\n"]

        # 타입별로 정리
        type_labels = {
            "feat": "🚀 새로운 기능",
            "fix": "🐛 버그 수정",
            "refactor": "♻️ 리팩토링",
            "docs": "📚 문서",
            "test": "✅ 테스트",
            "chore": "🔧 기타",
        }

        for type_name, subjects in by_type.items():
            label = type_labels.get(type_name, f"📌 {type_name}")
            lines.append(f"\n**{label}**")
            for subject in subjects:
                # 커밋 타입 접두사 제거
                # subject에서 "feat: " 같은 부분 제거
                clean_subject = subject
                if ":" in subject:
                    clean_subject = subject.split(":", 1)[1].strip()
                lines.append(f"- {clean_subject}")

        return "\n".join(lines)


# ============================================================
# 요약기 팩토리 함수
# ============================================================

def get_summarizer(
    provider: str = "auto",
    api_key: Optional[str] = None
) -> BaseSummarizer:
    """
    설정에 따라 적절한 요약기를 반환하는 팩토리 함수

    팩토리 패턴:
    - 객체 생성 로직을 별도 함수로 분리
    - 어떤 클래스의 객체를 만들지 결정하는 로직을 캡슐화

    매개변수:
        provider: "openai", "anthropic", "fallback", 또는 "auto"
        api_key: API 키 (없으면 환경변수에서 읽음)

    반환:
        BaseSummarizer를 상속한 요약기 객체
    """
    # auto: 환경변수에 있는 API 키에 따라 자동 선택
    if provider == "auto":
        if os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        else:
            provider = "fallback"

    # 제공자에 따라 적절한 요약기 반환
    if provider == "openai":
        return OpenAISummarizer(api_key=api_key)
    elif provider == "anthropic":
        return AnthropicSummarizer(api_key=api_key)
    else:
        return FallbackSummarizer()


# ============================================================
# 테스트용 코드
# ============================================================

if __name__ == "__main__":
    # 비동기 코드를 실행하려면 asyncio.run() 사용
    async def test():
        # 테스트용 커밋 데이터
        from datetime import datetime
        from core.models import CommitType

        test_commits = [
            CommitInfo(
                hash="abc1234",
                subject="feat: 사용자 로그인 기능 추가",
                author_email="dev@example.com",
                timestamp=datetime.now(),
                commit_type=CommitType.FEAT,
                insertions=150,
                deletions=20,
                changed_files=["auth.py", "login.html"]
            ),
            CommitInfo(
                hash="def5678",
                subject="fix: 비밀번호 검증 버그 수정",
                author_email="dev@example.com",
                timestamp=datetime.now(),
                commit_type=CommitType.FIX,
                insertions=10,
                deletions=5,
                changed_files=["auth.py"]
            )
        ]

        # 폴백 요약기 테스트 (API 없이)
        summarizer = FallbackSummarizer()
        result = await summarizer.summarize(test_commits)
        print("=== 폴백 요약 결과 ===")
        print(result)

    # 비동기 함수 실행
    asyncio.run(test())
