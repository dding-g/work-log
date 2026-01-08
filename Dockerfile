# ============================================================
# AWS Lambda용 Dockerfile
# ============================================================
#
# 이 Dockerfile은 FastAPI 앱을 AWS Lambda에서 실행하기 위한
# 컨테이너 이미지를 빌드합니다.
#
# 빌드 방법:
#   docker build -t work-log-lambda .
#
# 로컬 테스트:
#   docker run -p 9000:8080 work-log-lambda
#   curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
#     -d '{"httpMethod": "GET", "path": "/health"}'
#

# ============================================================
# 베이스 이미지 선택
# ============================================================

# AWS에서 제공하는 공식 Lambda Python 런타임 이미지
# - Lambda 실행에 필요한 모든 것이 미리 설정됨
# - python:3.11 대신 이걸 사용해야 Lambda에서 동작
FROM public.ecr.aws/lambda/python:3.11

# ============================================================
# 의존성 설치
# ============================================================

# requirements.txt를 먼저 복사 (Docker 캐시 활용)
# 의존성이 변경되지 않으면 이 레이어가 캐시됨
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# pip 업그레이드 및 의존성 설치
# --no-cache-dir: pip 캐시 사용 안 함 (이미지 크기 감소)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# 애플리케이션 코드 복사
# ============================================================

# LAMBDA_TASK_ROOT: Lambda가 코드를 찾는 기본 경로 (/var/task)
# 모든 소스 코드를 이 경로에 복사
COPY core/ ${LAMBDA_TASK_ROOT}/core/

# worklog 디렉토리 생성 (업무일지 저장용)
# Lambda는 /tmp만 쓰기 가능하므로 실제로는 /tmp/worklog 사용 권장
RUN mkdir -p ${LAMBDA_TASK_ROOT}/worklog

# ============================================================
# Lambda 핸들러 설정
# ============================================================

# CMD: Lambda 핸들러 위치 지정
# 형식: <모듈 경로>.<핸들러 함수>
# core.api 모듈의 handler 함수를 진입점으로 설정
CMD ["core.api.handler"]
