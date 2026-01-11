"""
github_client.py - GitHub API 클라이언트

Lambda 환경에서는 로컬 Git 저장소에 접근할 수 없으므로,
GitHub API를 사용하여 커밋 정보를 가져옵니다.
"""

import os
import httpx
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from core.models import CommitInfo, CommitType, CommitStats, QualityEvaluation
import re


class GitHubClient:
    """
    GitHub API를 사용하여 커밋 정보를 가져오는 클라이언트
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        """
        생성자

        매개변수:
            token: GitHub Personal Access Token (없으면 환경변수에서 읽음)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError(
                "GitHub 토큰이 필요합니다. "
                "GITHUB_TOKEN 환경변수를 설정하세요."
            )

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _parse_commit_type(self, subject: str) -> CommitType:
        """
        커밋 메시지에서 타입을 추출
        """
        pattern = r"^(feat|fix|refactor|docs|test|chore|style|perf|ci)(\(.+\))?:"
        match = re.match(pattern, subject, re.IGNORECASE)

        if match:
            commit_type_str = match.group(1).lower()
            try:
                return CommitType(commit_type_str)
            except ValueError:
                return CommitType.OTHER

        return CommitType.OTHER

    async def get_commits_for_date(
        self,
        owner: str,
        repo: str,
        target_date: date,
        author: Optional[str] = None
    ) -> List[CommitInfo]:
        """
        특정 날짜의 커밋 목록을 가져옴

        매개변수:
            owner: 저장소 소유자 (예: "ddingg")
            repo: 저장소 이름 (예: "work-log")
            target_date: 조회할 날짜
            author: 특정 작성자로 필터링 (선택)

        반환:
            CommitInfo 객체들의 리스트
        """
        # UTC 기준 날짜 범위 설정 (KST는 UTC+9)
        # KST 00:00:00 = UTC 전날 15:00:00
        # KST 23:59:59 = UTC 당일 14:59:59
        kst = timezone(timedelta(hours=9))
        start_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=kst)
        end_datetime = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=kst)

        # ISO 8601 형식으로 변환
        since = start_datetime.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        until = end_datetime.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params = {
            "since": since,
            "until": until,
            "per_page": 100
        }

        if author:
            params["author"] = author

        commits_list = []

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                print(f"GitHub API 오류: {response.status_code} - {response.text}")
                return []

            commits_data = response.json()

            for commit_data in commits_data:
                commit = commit_data["commit"]
                sha = commit_data["sha"][:7]
                subject = commit["message"].split("\n")[0]
                body = commit["message"][len(subject):].strip() or None
                author_email = commit["author"]["email"] if commit["author"] else "unknown"
                timestamp_str = commit["author"]["date"] if commit["author"] else None

                # timestamp 파싱
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.now(timezone.utc)

                # 커밋 상세 정보 가져오기 (변경된 파일, 라인 수)
                detail_url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{commit_data['sha']}"
                detail_response = await client.get(detail_url, headers=self.headers)

                insertions = 0
                deletions = 0
                changed_files = []

                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    stats = detail_data.get("stats", {})
                    insertions = stats.get("additions", 0)
                    deletions = stats.get("deletions", 0)

                    files = detail_data.get("files", [])
                    changed_files = [f["filename"] for f in files]

                commit_type = self._parse_commit_type(subject)

                commit_info = CommitInfo(
                    hash=sha,
                    subject=subject,
                    body=body,
                    author_email=author_email,
                    timestamp=timestamp.replace(tzinfo=None),
                    commit_type=commit_type,
                    changed_files=changed_files,
                    insertions=insertions,
                    deletions=deletions
                )

                commits_list.append(commit_info)

        return commits_list

    def calculate_stats(self, commits: List[CommitInfo]) -> CommitStats:
        """
        커밋 목록에서 통계 계산
        """
        stats = CommitStats()

        if not commits:
            return stats

        stats.total_commits = len(commits)
        stats.total_insertions = sum(c.insertions for c in commits)
        stats.total_deletions = sum(c.deletions for c in commits)

        all_files = set()
        for commit in commits:
            all_files.update(commit.changed_files)
        stats.total_files_changed = len(all_files)

        type_counts = {}
        for commit in commits:
            type_str = commit.commit_type.value
            type_counts[type_str] = type_counts.get(type_str, 0) + 1

        stats.commits_by_type = type_counts

        return stats

    def evaluate_quality(self, commits: List[CommitInfo]) -> QualityEvaluation:
        """
        커밋 품질 평가
        """
        evaluation = QualityEvaluation()

        if not commits:
            return evaluation

        score = 70

        # 잘한 점 평가
        conventional_commits = [
            c for c in commits
            if c.commit_type != CommitType.OTHER
        ]
        if conventional_commits:
            evaluation.good_points.append(
                f"커밋 컨벤션 준수: {len(conventional_commits)}개의 커밋이 "
                f"표준 형식(feat/fix 등)을 따름"
            )
            score += 10

        small_commits = [
            c for c in commits
            if len(c.changed_files) <= 5 and (c.insertions + c.deletions) <= 100
        ]
        if small_commits:
            evaluation.good_points.append(
                f"적절한 커밋 크기: {len(small_commits)}개의 커밋이 "
                f"작고 집중적임"
            )
            score += 10

        test_commits = [
            c for c in commits
            if c.commit_type == CommitType.TEST or
               any("test" in f.lower() for f in c.changed_files)
        ]
        if test_commits:
            evaluation.good_points.append(
                f"테스트 작성: {len(test_commits)}개의 테스트 관련 커밋"
            )
            score += 10

        # 개선할 점 평가
        large_commits = [
            c for c in commits
            if len(c.changed_files) > 10 or (c.insertions + c.deletions) > 300
        ]
        if large_commits:
            hashes = ", ".join(c.hash for c in large_commits[:3])
            evaluation.improvements.append(
                f"커밋 분리 필요: {len(large_commits)}개의 큰 커밋 발견 ({hashes})"
            )
            score -= 10

        vague_keywords = ["update", "fix", "change", "modify", "wip"]
        vague_commits = [
            c for c in commits
            if c.subject.lower().strip() in vague_keywords or
               len(c.subject) < 10
        ]
        if vague_commits:
            evaluation.improvements.append(
                f"커밋 메시지 개선 필요: {len(vague_commits)}개의 모호한 메시지"
            )
            score -= 10

        non_conventional = [
            c for c in commits
            if c.commit_type == CommitType.OTHER
        ]
        if len(non_conventional) > len(commits) // 2:
            evaluation.improvements.append(
                "커밋 컨벤션 적용 권장: feat:, fix: 등의 접두사 사용"
            )
            score -= 5

        evaluation.score = max(0, min(100, score))

        return evaluation
