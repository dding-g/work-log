"""
generator.py - Markdown 업무일지 생성기

이 파일은 분석된 커밋 데이터를 Markdown 형식의 업무일지로 변환합니다.
Markdown은 텍스트 기반 문서 형식으로, GitHub, Notion 등에서 널리 사용됩니다.

Markdown 기본 문법:
- # 제목1, ## 제목2, ### 제목3
- **굵게**, *기울임*
- - 목록 항목
- | 표 | 형식 |
"""

# ============================================================
# 임포트
# ============================================================

# 날짜/시간 처리
from datetime import date, datetime

# 파일 경로 처리
# Path: 운영체제에 상관없이 파일 경로를 다루는 객체
from pathlib import Path

# 타입 힌트
from typing import Optional

# 우리가 만든 모델들
from core.models import WorkLog, CommitInfo, CommitType


# ============================================================
# MarkdownGenerator 클래스
# ============================================================

class MarkdownGenerator:
    """
    업무일지를 Markdown 파일로 생성하는 클래스

    책임:
    - WorkLog 객체를 Markdown 문자열로 변환
    - 파일로 저장
    """

    def __init__(self, output_dir: str = "./worklog"):
        """
        생성자

        매개변수:
            output_dir: 업무일지를 저장할 디렉토리 경로
        """
        # Path 객체로 변환
        # Path는 문자열보다 경로 처리에 편리함
        self.output_dir = Path(output_dir)

        # 디렉토리가 없으면 생성
        # mkdir(): 디렉토리 생성
        # parents=True: 상위 디렉토리도 함께 생성
        # exist_ok=True: 이미 있어도 에러 안 남
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _format_commit_list(
        self,
        commits: list,
        commit_type: CommitType
    ) -> str:
        """
        특정 타입의 커밋들을 Markdown 목록으로 변환

        매개변수:
            commits: CommitInfo 리스트
            commit_type: 필터링할 커밋 타입

        반환:
            Markdown 형식의 문자열
        """
        # 해당 타입의 커밋만 필터링
        # 리스트 컴프리헨션으로 필터링
        filtered = [c for c in commits if c.commit_type == commit_type]

        # 없으면 빈 문자열
        if not filtered:
            return ""

        # 결과 문자열 생성
        lines = []
        for commit in filtered:
            # 커밋 메시지에서 타입 접두사 제거
            subject = commit.subject
            if ":" in subject:
                # split(":", 1): 첫 번째 ":"만 기준으로 분리
                subject = subject.split(":", 1)[1].strip()

            # 백틱(`)으로 해시 감싸기: 코드 스타일로 표시
            lines.append(f"- `{commit.hash}` {subject}")

        return "\n".join(lines)

    def _get_day_of_week_korean(self, target_date: date) -> str:
        """
        날짜에서 한국어 요일 반환

        weekday(): 0=월요일, 1=화요일, ..., 6=일요일
        """
        days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        return days[target_date.weekday()]

    def generate(self, worklog: WorkLog) -> str:
        """
        WorkLog 객체를 Markdown 문자열로 변환

        매개변수:
            worklog: 업무일지 데이터

        반환:
            Markdown 형식의 문자열
        """
        # f-string과 삼중 따옴표로 여러 줄 문자열 생성
        # 변수는 {변수명} 형식으로 삽입

        # 헤더 부분
        markdown = f"""# 업무일지 - {worklog.target_date} ({worklog.day_of_week})

> 자동 생성됨 | 저장소: {worklog.repository_name}

"""

        # ===== AI 요약 섹션 =====
        if worklog.ai_summary:
            markdown += f"""## 📝 AI 요약

{worklog.ai_summary}

"""

        # ===== 작업 요약 섹션 =====
        markdown += "## 📋 작업 요약\n\n"

        # 커밋이 없는 경우
        if not worklog.commits:
            markdown += "오늘은 커밋이 없습니다.\n\n"
        else:
            # 타입별로 커밋 목록 생성
            # 각 타입에 대해 이모지와 제목 정의
            type_sections = [
                (CommitType.FEAT, "### 🚀 새로운 기능"),
                (CommitType.FIX, "### 🐛 버그 수정"),
                (CommitType.REFACTOR, "### ♻️ 리팩토링"),
                (CommitType.DOCS, "### 📚 문서"),
                (CommitType.TEST, "### ✅ 테스트"),
                (CommitType.PERF, "### ⚡ 성능 개선"),
                (CommitType.CHORE, "### 🔧 기타 작업"),
                (CommitType.OTHER, "### 📌 기타"),
            ]

            for commit_type, title in type_sections:
                commit_list = self._format_commit_list(
                    worklog.commits,
                    commit_type
                )
                if commit_list:
                    markdown += f"{title}\n\n{commit_list}\n\n"

        # ===== 통계 섹션 =====
        stats = worklog.stats
        markdown += f"""## 📊 통계

| 항목 | 수치 |
|------|------|
| 커밋 수 | {stats.total_commits} |
| 변경 파일 | {stats.total_files_changed} |
| 추가 라인 | +{stats.total_insertions} |
| 삭제 라인 | -{stats.total_deletions} |

"""

        # ===== 품질 평가 섹션 =====
        quality = worklog.quality

        # 잘한 점
        markdown += "## ✅ 잘한 점\n\n"
        if quality.good_points:
            for i, point in enumerate(quality.good_points, 1):
                # enumerate(list, 1): 1부터 시작하는 번호와 함께 순회
                markdown += f"{i}. {point}\n"
        else:
            markdown += "- 특이사항 없음\n"
        markdown += "\n"

        # 개선할 점
        markdown += "## 🔧 개선할 점\n\n"
        if quality.improvements:
            for i, point in enumerate(quality.improvements, 1):
                markdown += f"{i}. {point}\n"
        else:
            markdown += "- 특이사항 없음\n"
        markdown += "\n"

        # 품질 점수 (프로그레스 바 형태로)
        score = quality.score
        filled = score // 10  # 10점당 1칸
        empty = 10 - filled
        progress_bar = "█" * filled + "░" * empty
        markdown += f"**품질 점수**: {progress_bar} {score}/100\n\n"

        # ===== Follow-up 섹션 =====
        markdown += """## 💡 Follow-up

- [ ] 코드 리뷰 반영사항 확인
- [ ] 테스트 커버리지 확인
- [ ] 문서 업데이트 필요 여부 검토

"""

        # ===== 푸터 =====
        generated_time = worklog.generated_at.strftime("%Y-%m-%d %H:%M:%S")
        # strftime(): datetime을 문자열로 포맷팅
        # %Y: 4자리 연도, %m: 2자리 월, %d: 2자리 일
        # %H: 24시간 시, %M: 분, %S: 초

        markdown += f"""---
*Generated by Work-Log Automation at {generated_time}*
"""

        return markdown

    def save(self, worklog: WorkLog) -> Path:
        """
        업무일지를 파일로 저장

        매개변수:
            worklog: 업무일지 데이터

        반환:
            저장된 파일 경로 (Path 객체)
        """
        # Markdown 생성
        content = self.generate(worklog)

        # 파일명 생성: YYYY-MM-DD.md
        filename = f"{worklog.target_date}.md"
        file_path = self.output_dir / filename
        # Path 객체는 / 연산자로 경로 결합 가능

        # 파일 쓰기
        # write_text(): 텍스트를 파일에 저장
        # encoding="utf-8": 한글 등 유니코드 문자 지원
        file_path.write_text(content, encoding="utf-8")

        return file_path

    def generate_empty(self, target_date: date, repo_name: str) -> str:
        """
        커밋이 없는 날의 간단한 업무일지 생성

        매개변수:
            target_date: 대상 날짜
            repo_name: 저장소 이름

        반환:
            Markdown 문자열
        """
        day_of_week = self._get_day_of_week_korean(target_date)
        generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""# 업무일지 - {target_date} ({day_of_week})

> 자동 생성됨 | 저장소: {repo_name}

## 📋 작업 요약

오늘은 커밋이 없습니다.

---
*Generated by Work-Log Automation at {generated_time}*
"""


# ============================================================
# 테스트용 코드
# ============================================================

if __name__ == "__main__":
    # 테스트용 데이터 생성
    from datetime import datetime
    from core.models import (
        WorkLog, CommitInfo, CommitStats,
        QualityEvaluation, CommitType
    )

    # 테스트 커밋
    test_commits = [
        CommitInfo(
            hash="abc1234",
            subject="feat: 로그인 기능 추가",
            author_email="dev@example.com",
            timestamp=datetime.now(),
            commit_type=CommitType.FEAT,
            changed_files=["auth.py", "login.html"],
            insertions=150,
            deletions=20
        ),
        CommitInfo(
            hash="def5678",
            subject="fix: 비밀번호 검증 오류 수정",
            author_email="dev@example.com",
            timestamp=datetime.now(),
            commit_type=CommitType.FIX,
            changed_files=["auth.py"],
            insertions=10,
            deletions=5
        )
    ]

    # 테스트 WorkLog 생성
    test_worklog = WorkLog(
        target_date=date.today(),
        day_of_week="수요일",
        repository_name="test-repo",
        commits=test_commits,
        stats=CommitStats(
            total_commits=2,
            total_files_changed=2,
            total_insertions=160,
            total_deletions=25,
            commits_by_type={"feat": 1, "fix": 1}
        ),
        quality=QualityEvaluation(
            good_points=["커밋 컨벤션 준수", "적절한 커밋 크기"],
            improvements=["테스트 코드 추가 필요"],
            score=85
        ),
        ai_summary="- 사용자 로그인 기능을 새로 구현했습니다.\n- 비밀번호 검증 관련 버그를 수정했습니다."
    )

    # 생성기 테스트
    generator = MarkdownGenerator("./worklog")
    markdown = generator.generate(test_worklog)

    print("=== 생성된 Markdown ===")
    print(markdown)

    # 파일로 저장
    saved_path = generator.save(test_worklog)
    print(f"\n파일 저장됨: {saved_path}")
