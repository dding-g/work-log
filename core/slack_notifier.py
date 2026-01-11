"""
slack_notifier.py - Slack 알림 전송

업무일지 생성 결과를 Slack으로 전송합니다.
"""

import os
import httpx
from datetime import date
from typing import Optional
from core.models import WorkLog


class SlackNotifier:
    """
    Slack으로 업무일지 알림을 전송하는 클라이언트
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        생성자

        매개변수:
            webhook_url: Slack Webhook URL (없으면 환경변수에서 읽음)
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError(
                "Slack Webhook URL이 필요합니다. "
                "SLACK_WEBHOOK_URL 환경변수를 설정하세요."
            )

    async def send_worklog(
        self,
        worklog: WorkLog,
        s3_url: Optional[str] = None
    ) -> bool:
        """
        업무일지를 Slack으로 전송

        매개변수:
            worklog: 업무일지 데이터
            s3_url: S3 저장 URL (선택)

        반환:
            성공 여부
        """
        # 커밋 타입별 통계
        type_stats = worklog.stats.commits_by_type
        type_summary = ", ".join([
            f"{k}: {v}개" for k, v in type_stats.items()
        ]) if type_stats else "없음"

        # AI 요약 (있으면)
        ai_summary_text = worklog.ai_summary or "요약 없음"
        # 너무 길면 자르기
        if len(ai_summary_text) > 500:
            ai_summary_text = ai_summary_text[:500] + "..."

        # Slack 블록 구성
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📝 업무일지 - {worklog.target_date} ({worklog.day_of_week})",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📊 통계*\n"
                            f"• 저장소: `{worklog.repository_name}`\n"
                            f"• 커밋 수: {worklog.stats.total_commits}개\n"
                            f"• 변경 파일: {worklog.stats.total_files_changed}개\n"
                            f"• 코드 변경: +{worklog.stats.total_insertions} / -{worklog.stats.total_deletions} lines\n"
                            f"• 타입별: {type_summary}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📋 AI 요약*\n{ai_summary_text}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✅ 품질 점수*: {worklog.quality.score}/100"
                }
            }
        ]

        # S3 URL이 있으면 추가
        if s3_url:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📁 저장 위치: `{s3_url}`"
                    }
                ]
            })

        # 푸터
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🤖 자동 생성됨 | {worklog.generated_at.strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })

        # Slack으로 전송
        payload = {"blocks": blocks}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json=payload,
                timeout=30.0
            )

            return response.status_code == 200

    async def send_error(
        self,
        target_date: date,
        error_message: str,
        repo_info: Optional[str] = None
    ) -> bool:
        """
        에러 알림을 Slack으로 전송

        매개변수:
            target_date: 대상 날짜
            error_message: 에러 메시지
            repo_info: 저장소 정보 (선택)

        반환:
            성공 여부
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚠️ 업무일지 생성 실패 - {target_date}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*오류 내용*\n```{error_message}```"
                }
            }
        ]

        if repo_info:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"저장소: {repo_info}"
                    }
                ]
            })

        payload = {"blocks": blocks}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json=payload,
                timeout=30.0
            )

            return response.status_code == 200

    async def send_no_commits(
        self,
        target_date: date,
        repo_name: str
    ) -> bool:
        """
        커밋이 없을 때 알림 전송

        매개변수:
            target_date: 대상 날짜
            repo_name: 저장소 이름

        반환:
            성공 여부
        """
        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📭 *{target_date}* ({repo_name}): 오늘은 커밋이 없습니다."
                    }
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json=payload,
                timeout=30.0
            )

            return response.status_code == 200
