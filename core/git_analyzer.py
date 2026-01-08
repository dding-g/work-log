"""
git_analyzer.py - Git 저장소 분석기

이 파일은 Git 저장소에서 커밋 정보를 가져오고 분석합니다.
GitPython이라는 라이브러리를 사용해서 Git 명령어를 파이썬으로 실행합니다.

GitPython은 내부적으로 git 명령어를 실행하므로,
시스템에 git이 설치되어 있어야 합니다.
"""

# ============================================================
# 임포트
# ============================================================

# 날짜/시간 관련
from datetime import date, datetime, timedelta
# timedelta: 시간의 차이를 나타냄 (예: 1일, 2시간 등)

# 타입 힌트
from typing import List, Optional

# 정규표현식: 문자열 패턴 매칭에 사용
# 예: "feat: 기능추가"에서 "feat"만 추출
import re

# GitPython: Git을 파이썬으로 다루는 라이브러리
# Repo: Git 저장소를 나타내는 클래스
# InvalidGitRepositoryError: Git 저장소가 아닐 때 발생하는 에러
from git import Repo, InvalidGitRepositoryError

# 우리가 만든 데이터 모델들을 가져옴
from core.models import CommitInfo, CommitType, CommitStats, QualityEvaluation


# ============================================================
# GitAnalyzer 클래스
# ============================================================

class GitAnalyzer:
    """
    Git 저장소를 분석하는 클래스

    클래스(class)란?
    - 관련된 데이터와 기능을 하나로 묶어놓은 것
    - 마치 "자동차 설계도"와 같아요
    - 이 설계도로 실제 자동차(객체)를 만들 수 있어요

    사용 예시:
        analyzer = GitAnalyzer("/path/to/repo")  # 객체 생성
        commits = analyzer.get_commits_for_date(date.today())  # 메서드 호출
    """

    def __init__(self, repo_path: str = "."):
        """
        생성자 (Constructor) - 객체가 만들어질 때 자동으로 실행됨

        __init__은 특별한 메서드로, 객체를 초기화합니다.
        self는 "이 객체 자신"을 가리킵니다.

        매개변수:
            repo_path: Git 저장소 경로 (기본값: 현재 디렉토리 ".")
        """
        # self.repo_path: 이 객체의 속성(attribute)으로 저장
        # 나중에 self.repo_path로 접근 가능
        self.repo_path = repo_path

        # Git 저장소가 유효한지 확인하고 Repo 객체 생성
        # try-except: 에러가 발생할 수 있는 코드를 안전하게 실행
        try:
            # Repo(): GitPython의 저장소 객체 생성
            self.repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            # Git 저장소가 아니면 에러 발생
            # raise: 에러를 발생시킴
            raise ValueError(f"'{repo_path}'는 유효한 Git 저장소가 아닙니다.")

    def get_repo_name(self) -> str:
        """
        저장소 이름을 반환

        -> str: 이 함수가 문자열을 반환한다는 타입 힌트
        """
        # working_dir: 저장소의 작업 디렉토리 경로
        # split("/"): 경로를 "/"로 나눔
        # [-1]: 리스트의 마지막 요소 (폴더 이름)
        return self.repo.working_dir.split("/")[-1]

    def get_user_email(self) -> str:
        """
        현재 Git 설정의 사용자 이메일을 반환
        """
        # config_reader(): Git 설정을 읽는 객체
        # get_value("user", "email"): user.email 설정값 가져오기
        try:
            return self.repo.config_reader().get_value("user", "email")
        except:
            # 설정이 없으면 빈 문자열 반환
            return ""

    def _parse_commit_type(self, subject: str) -> CommitType:
        """
        커밋 메시지에서 타입을 추출

        메서드 이름이 _로 시작하면 "내부용"이라는 관례입니다.
        외부에서 직접 호출하지 않고, 클래스 내부에서만 사용합니다.

        예시:
            "feat: 로그인 추가" → CommitType.FEAT
            "fix(auth): 버그 수정" → CommitType.FIX
        """
        # 정규표현식 패턴
        # ^: 문자열의 시작
        # (feat|fix|...): 이 중 하나와 매칭
        # (\(.+\))?: 괄호 안에 뭔가 있을 수도 있음 (예: feat(auth))
        # :: 콜론
        pattern = r"^(feat|fix|refactor|docs|test|chore|style|perf|ci)(\(.+\))?:"

        # re.match(): 문자열 시작부터 패턴과 매칭 시도
        # re.IGNORECASE: 대소문자 구분 안 함
        match = re.match(pattern, subject, re.IGNORECASE)

        if match:
            # group(1): 첫 번째 괄호 안의 내용 (feat, fix 등)
            # lower(): 소문자로 변환
            commit_type_str = match.group(1).lower()

            # 문자열을 CommitType enum으로 변환
            # CommitType("feat") → CommitType.FEAT
            try:
                return CommitType(commit_type_str)
            except ValueError:
                return CommitType.OTHER

        # 패턴에 맞지 않으면 OTHER
        return CommitType.OTHER

    def _get_commit_stats(self, commit) -> tuple:
        """
        커밋의 변경 통계를 가져옴

        반환: (변경된 파일 목록, 추가된 라인 수, 삭제된 라인 수)

        tuple(튜플): 여러 값을 하나로 묶는 자료형
        리스트와 비슷하지만 수정 불가능(immutable)
        """
        changed_files = []  # 빈 리스트
        insertions = 0
        deletions = 0

        try:
            # 부모 커밋이 있는 경우 (첫 커밋이 아닌 경우)
            if commit.parents:
                # 부모 커밋과 비교하여 diff 생성
                # parents[0]: 첫 번째 부모 커밋
                diff = commit.parents[0].diff(commit)

                # diff를 순회하면서 파일 목록 수집
                for d in diff:
                    # a_path 또는 b_path에서 파일 경로 가져오기
                    # a_path: 이전 파일, b_path: 새 파일
                    if d.a_path:
                        changed_files.append(d.a_path)
                    elif d.b_path:
                        changed_files.append(d.b_path)

                # stats: 커밋의 통계 정보
                # total: 전체 통계 딕셔너리
                stats = commit.stats.total
                insertions = stats.get("insertions", 0)  # 없으면 0
                deletions = stats.get("deletions", 0)

        except Exception as e:
            # 에러 발생 시 기본값 반환
            # 실제 프로덕션에서는 로깅을 하는 것이 좋습니다
            pass

        return changed_files, insertions, deletions

    def get_commits_for_date(
        self,
        target_date: date,
        author_email: Optional[str] = None
    ) -> List[CommitInfo]:
        """
        특정 날짜의 커밋 목록을 가져옴

        매개변수:
            target_date: 조회할 날짜
            author_email: 특정 작성자로 필터링 (None이면 모든 작성자)

        반환:
            CommitInfo 객체들의 리스트
        """
        # 결과를 담을 빈 리스트
        commits_list = []

        # 날짜 범위 설정: target_date 00:00:00 ~ 23:59:59
        # datetime.combine(): date와 time을 합쳐서 datetime 생성
        # datetime.min.time(): 00:00:00
        # datetime.max.time(): 23:59:59.999999
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        # 작성자 이메일 설정 (없으면 현재 사용자)
        if author_email is None:
            author_email = self.get_user_email()

        # iter_commits(): 저장소의 커밋을 순회
        # 반환되는 것은 제너레이터(generator)로, 메모리 효율적
        try:
            # 모든 커밋을 순회
            for commit in self.repo.iter_commits():
                # 커밋 시각을 datetime으로 변환
                # committed_datetime: 커밋된 시각 (timezone aware)
                # replace(tzinfo=None): timezone 정보 제거 (비교를 위해)
                commit_datetime = commit.committed_datetime.replace(tzinfo=None)

                # 날짜 범위 확인
                if commit_datetime < start_datetime:
                    # 너무 오래된 커밋이면 중단
                    # Git 로그는 최신순이므로, 여기서 멈춰도 됨
                    break

                if commit_datetime > end_datetime:
                    # 아직 해당 날짜에 도달하지 않음
                    continue

                # 작성자 확인 (이메일이 비어있지 않으면)
                if author_email and commit.author.email != author_email:
                    continue

                # 커밋 통계 가져오기
                changed_files, insertions, deletions = self._get_commit_stats(commit)

                # 커밋 타입 파싱
                commit_type = self._parse_commit_type(commit.summary)

                # CommitInfo 객체 생성
                commit_info = CommitInfo(
                    hash=commit.hexsha[:7],  # 해시의 앞 7자리만
                    subject=commit.summary,   # 커밋 메시지 첫 줄
                    body=commit.message[len(commit.summary):].strip() or None,
                    author_email=commit.author.email,
                    timestamp=commit_datetime,
                    commit_type=commit_type,
                    changed_files=changed_files,
                    insertions=insertions,
                    deletions=deletions
                )

                # 리스트에 추가
                commits_list.append(commit_info)

        except Exception as e:
            # 에러 발생 시 빈 리스트 반환
            print(f"커밋 조회 중 에러 발생: {e}")

        return commits_list

    def calculate_stats(self, commits: List[CommitInfo]) -> CommitStats:
        """
        커밋 목록에서 통계 계산

        매개변수:
            commits: CommitInfo 객체들의 리스트

        반환:
            CommitStats 객체
        """
        # 통계 객체 생성
        stats = CommitStats()

        # 커밋이 없으면 빈 통계 반환
        if not commits:
            return stats

        # 기본 통계 계산
        stats.total_commits = len(commits)  # len(): 리스트 길이

        # sum(): 합계 계산
        # 리스트 컴프리헨션: [c.insertions for c in commits]
        # commits의 각 c에 대해 c.insertions를 모아서 리스트로 만듦
        stats.total_insertions = sum(c.insertions for c in commits)
        stats.total_deletions = sum(c.deletions for c in commits)

        # 변경된 파일 수 계산 (중복 제거)
        # set(): 집합 - 중복을 자동으로 제거
        all_files = set()
        for commit in commits:
            # update(): 여러 요소를 한번에 추가
            all_files.update(commit.changed_files)
        stats.total_files_changed = len(all_files)

        # 타입별 커밋 수 계산
        type_counts = {}  # 빈 딕셔너리
        for commit in commits:
            # commit_type.value: enum의 실제 값 ("feat", "fix" 등)
            type_str = commit.commit_type.value

            # 딕셔너리에 카운트 추가
            # get(key, default): key가 없으면 default 반환
            type_counts[type_str] = type_counts.get(type_str, 0) + 1

        stats.commits_by_type = type_counts

        return stats

    def evaluate_quality(self, commits: List[CommitInfo]) -> QualityEvaluation:
        """
        커밋 품질 평가

        커밋 메시지, 크기, 패턴 등을 분석해서
        잘한 점과 개선할 점을 찾아냅니다.
        """
        # 평가 객체 생성
        evaluation = QualityEvaluation()

        # 커밋이 없으면 빈 평가 반환
        if not commits:
            return evaluation

        # 점수 시작값
        score = 70  # 기본 점수

        # ===== 잘한 점 평가 =====

        # 1. 컨벤션을 따르는 커밋이 있는지
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

        # 2. 작은 커밋 (파일 5개 이하, 변경 100줄 이하)
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

        # 3. 테스트 관련 커밋이 있는지
        test_commits = [
            c for c in commits
            if c.commit_type == CommitType.TEST or
               any("test" in f.lower() for f in c.changed_files)
            # any(): 하나라도 True면 True
        ]
        if test_commits:
            evaluation.good_points.append(
                f"테스트 작성: {len(test_commits)}개의 테스트 관련 커밋"
            )
            score += 10

        # ===== 개선할 점 평가 =====

        # 1. 너무 큰 커밋 (파일 10개 초과 또는 변경 300줄 초과)
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

        # 2. 모호한 커밋 메시지
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

        # 3. 컨벤션을 따르지 않는 커밋
        non_conventional = [
            c for c in commits
            if c.commit_type == CommitType.OTHER
        ]
        if len(non_conventional) > len(commits) // 2:
            # 절반 이상이 컨벤션을 안 따르면
            evaluation.improvements.append(
                "커밋 컨벤션 적용 권장: feat:, fix: 등의 접두사 사용"
            )
            score -= 5

        # 점수 범위 조정 (0~100)
        # max(0, min(100, score)): 0보다 작으면 0, 100보다 크면 100
        evaluation.score = max(0, min(100, score))

        return evaluation


# ============================================================
# 테스트용 코드
# ============================================================

# 이 파일을 직접 실행할 때만 아래 코드가 실행됨
# 다른 파일에서 import할 때는 실행되지 않음
if __name__ == "__main__":
    # 현재 디렉토리를 분석
    analyzer = GitAnalyzer(".")

    print(f"저장소 이름: {analyzer.get_repo_name()}")
    print(f"사용자 이메일: {analyzer.get_user_email()}")

    # 어제 커밋 조회
    from datetime import date, timedelta
    yesterday = date.today() - timedelta(days=1)
    commits = analyzer.get_commits_for_date(yesterday)

    print(f"\n어제({yesterday})의 커밋 수: {len(commits)}")
    for c in commits:
        print(f"  - {c.hash}: {c.subject}")
