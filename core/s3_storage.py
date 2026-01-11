"""
s3_storage.py - S3 스토리지 클라이언트

업무일지를 S3에 저장하는 기능을 제공합니다.
"""

import os
import boto3
from datetime import date
from typing import Optional


class S3Storage:
    """
    S3에 업무일지를 저장하는 클라이언트
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        prefix: str = "worklogs"
    ):
        """
        생성자

        매개변수:
            bucket_name: S3 버킷 이름 (없으면 환경변수에서 읽음)
            prefix: S3 키 접두사 (폴더 역할)
        """
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError(
                "S3 버킷 이름이 필요합니다. "
                "S3_BUCKET_NAME 환경변수를 설정하세요."
            )

        self.prefix = prefix
        self.s3_client = boto3.client("s3")

    def save_worklog(
        self,
        content: str,
        target_date: date,
        repo_name: str
    ) -> str:
        """
        업무일지를 S3에 저장

        매개변수:
            content: Markdown 형식의 업무일지 내용
            target_date: 대상 날짜
            repo_name: 저장소 이름

        반환:
            S3 객체 키
        """
        # S3 키 생성: worklogs/repo_name/2024/01/2024-01-15.md
        key = (
            f"{self.prefix}/{repo_name}/"
            f"{target_date.year}/{target_date.month:02d}/"
            f"{target_date}.md"
        )

        # S3에 업로드
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
            Metadata={
                "target-date": str(target_date),
                "repository": repo_name
            }
        )

        return key

    def get_worklog(self, key: str) -> Optional[str]:
        """
        S3에서 업무일지 가져오기

        매개변수:
            key: S3 객체 키

        반환:
            Markdown 내용 또는 None
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response["Body"].read().decode("utf-8")
        except self.s3_client.exceptions.NoSuchKey:
            return None

    def list_worklogs(self, repo_name: Optional[str] = None) -> list:
        """
        저장된 업무일지 목록 조회

        매개변수:
            repo_name: 특정 저장소로 필터링 (선택)

        반환:
            S3 객체 키 목록
        """
        prefix = self.prefix
        if repo_name:
            prefix = f"{self.prefix}/{repo_name}/"

        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix
        )

        keys = []
        for obj in response.get("Contents", []):
            if obj["Key"].endswith(".md"):
                keys.append(obj["Key"])

        return sorted(keys, reverse=True)

    def get_s3_url(self, key: str) -> str:
        """
        S3 객체의 URL 반환

        매개변수:
            key: S3 객체 키

        반환:
            S3 URL
        """
        return f"s3://{self.bucket_name}/{key}"
