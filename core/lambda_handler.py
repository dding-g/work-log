"""
lambda_handler.py - AWS Lambda 핸들러

EventBridge에서 매일 자정에 트리거되는 Lambda 핸들러입니다.
GitHub API를 통해 커밋을 가져오고, S3에 저장하고, Slack으로 알림을 보냅니다.
"""

import os
import json
import asyncio
from datetime import date, timedelta
from typing import Any, Dict

from core.github_client import GitHubClient
from core.s3_storage import S3Storage
from core.slack_notifier import SlackNotifier
from core.summarizer import get_summarizer
from core.generator import MarkdownGenerator
from core.models import WorkLog


def get_day_of_week(target_date: date) -> str:
    """날짜에서 한국어 요일 반환"""
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return days[target_date.weekday()]


async def generate_worklog_async(
    owner: str,
    repo: str,
    target_date: date,
    use_ai_summary: bool = True,
    author: str = None
) -> Dict[str, Any]:
    """
    업무일지 생성 비동기 함수

    매개변수:
        owner: GitHub 저장소 소유자
        repo: GitHub 저장소 이름
        target_date: 대상 날짜
        use_ai_summary: AI 요약 사용 여부
        author: 특정 작성자로 필터링 (선택)

    반환:
        결과 딕셔너리
    """
    result = {
        "success": False,
        "error": None,
        "worklog": None,
        "s3_url": None,
        "commits_count": 0
    }

    try:
        # 1. GitHub에서 커밋 가져오기
        github_client = GitHubClient()
        commits = await github_client.get_commits_for_date(
            owner=owner,
            repo=repo,
            target_date=target_date,
            author=author
        )

        result["commits_count"] = len(commits)

        # 커밋이 없는 경우
        if not commits:
            # Slack으로 알림 (선택적)
            if os.getenv("SLACK_WEBHOOK_URL"):
                slack = SlackNotifier()
                await slack.send_no_commits(target_date, repo)

            result["success"] = True
            result["error"] = "커밋이 없습니다."
            return result

        # 2. 통계 및 품질 평가
        stats = github_client.calculate_stats(commits)
        quality = github_client.evaluate_quality(commits)

        # 3. AI 요약 (선택적)
        ai_summary = None
        if use_ai_summary:
            try:
                summarizer = get_summarizer("auto")
                ai_summary = await summarizer.summarize(commits)
            except Exception as e:
                ai_summary = f"[요약 생성 실패: {str(e)}]"

        # 4. WorkLog 객체 생성
        worklog = WorkLog(
            target_date=target_date,
            day_of_week=get_day_of_week(target_date),
            repository_name=repo,
            commits=commits,
            stats=stats,
            quality=quality,
            ai_summary=ai_summary
        )

        # 5. Markdown 생성
        generator = MarkdownGenerator("/tmp/worklog")
        markdown_content = generator.generate(worklog)

        # 6. S3에 저장
        s3_url = None
        if os.getenv("S3_BUCKET_NAME"):
            try:
                s3_storage = S3Storage()
                s3_key = s3_storage.save_worklog(
                    content=markdown_content,
                    target_date=target_date,
                    repo_name=repo
                )
                s3_url = s3_storage.get_s3_url(s3_key)
                result["s3_url"] = s3_url
            except Exception as e:
                print(f"S3 저장 실패: {e}")

        # 7. Slack 알림
        if os.getenv("SLACK_WEBHOOK_URL"):
            try:
                slack = SlackNotifier()
                await slack.send_worklog(worklog, s3_url)
            except Exception as e:
                print(f"Slack 전송 실패: {e}")

        result["success"] = True
        result["worklog"] = worklog.model_dump(mode="json")

    except Exception as e:
        result["error"] = str(e)

        # 에러 Slack 알림
        if os.getenv("SLACK_WEBHOOK_URL"):
            try:
                slack = SlackNotifier()
                await slack.send_error(
                    target_date=target_date,
                    error_message=str(e),
                    repo_info=f"{owner}/{repo}"
                )
            except:
                pass

    return result


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda 핸들러

    EventBridge 또는 직접 호출로 트리거됩니다.

    이벤트 형식 (직접 호출 시):
    {
        "owner": "ddingg",
        "repo": "work-log",
        "target_date": "2024-01-15",  // 선택, 기본값: 오늘
        "use_ai_summary": true,        // 선택, 기본값: true
        "author": "user@example.com"   // 선택
    }

    EventBridge 이벤트 형식:
    {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        ...
    }
    """
    print(f"Event received: {json.dumps(event)}")

    # EventBridge 스케줄 이벤트인지 확인
    is_scheduled = event.get("source") == "aws.events"

    # 환경변수에서 기본값 가져오기
    default_owner = os.getenv("GITHUB_OWNER", "ddingg")
    default_repo = os.getenv("GITHUB_REPO", "work-log")

    # 파라미터 추출
    if is_scheduled:
        # EventBridge 스케줄 이벤트: 환경변수에서 설정 가져오기
        owner = default_owner
        repo = default_repo
        target_date = date.today()  # 오늘 날짜
        use_ai_summary = os.getenv("USE_AI_SUMMARY", "true").lower() == "true"
        author = os.getenv("GITHUB_AUTHOR")
    else:
        # 직접 호출: 이벤트에서 파라미터 추출
        owner = event.get("owner", default_owner)
        repo = event.get("repo", default_repo)

        target_date_str = event.get("target_date")
        if target_date_str:
            target_date = date.fromisoformat(target_date_str)
        else:
            target_date = date.today()

        use_ai_summary = event.get("use_ai_summary", True)
        author = event.get("author")

    print(f"Processing: {owner}/{repo} for {target_date}")

    # 비동기 함수 실행
    result = asyncio.run(
        generate_worklog_async(
            owner=owner,
            repo=repo,
            target_date=target_date,
            use_ai_summary=use_ai_summary,
            author=author
        )
    )

    return {
        "statusCode": 200 if result["success"] else 500,
        "body": json.dumps(result, ensure_ascii=False, default=str)
    }


# 테스트용 코드
if __name__ == "__main__":
    # 로컬 테스트
    test_event = {
        "owner": "ddingg",
        "repo": "work-log",
        "target_date": str(date.today())
    }

    result = handler(test_event, None)
    print(json.dumps(result, indent=2, ensure_ascii=False))
