#!/bin/bash
#
# Slack 알림 스크립트
# 생성된 업무일지를 Slack으로 전송합니다.
#

set -euo pipefail

# ==================== 설정 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/config/config.env"

# 설정 파일 로드
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# 필수 환경 변수
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
SLACK_CHANNEL="${SLACK_CHANNEL:-#general}"
SLACK_USERNAME="${SLACK_USERNAME:-Work-Log Bot}"
SLACK_ICON_EMOJI="${SLACK_ICON_EMOJI:-:memo:}"

# ==================== 함수 ====================

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

check_requirements() {
    if [[ -z "$SLACK_WEBHOOK_URL" ]]; then
        log_error "SLACK_WEBHOOK_URL이 설정되지 않았습니다."
        log_error "config/config.env 파일에 SLACK_WEBHOOK_URL을 설정해주세요."
        exit 1
    fi

    if ! command -v curl &> /dev/null; then
        log_error "curl이 설치되어 있지 않습니다."
        exit 1
    fi
}

# Markdown을 Slack mrkdwn 형식으로 변환
convert_md_to_slack() {
    local content=$1

    # 기본 변환
    content=$(echo "$content" | sed \
        -e 's/^# \(.*\)/*\1*/g' \
        -e 's/^## \(.*\)/*\1*/g' \
        -e 's/^### \(.*\)/*\1*/g' \
        -e 's/\*\*\([^*]*\)\*\*/*\1*/g' \
        -e 's/`\([^`]*\)`/`\1`/g')

    echo "$content"
}

# 파일 내용을 Slack Block으로 변환
create_slack_blocks() {
    local file_path=$1
    local content
    content=$(cat "$file_path")

    # 제목 추출 (첫 번째 # 라인)
    local title
    title=$(echo "$content" | grep -m1 "^# " | sed 's/^# //')

    # 섹션별 추출
    local summary
    summary=$(echo "$content" | sed -n '/## 📋 작업 요약/,/## 📊/p' | head -n -1 | tail -n +2)

    local stats
    stats=$(echo "$content" | sed -n '/## 📊 통계/,/## ✅/p' | head -n -1 | tail -n +2)

    local good_points
    good_points=$(echo "$content" | sed -n '/## ✅ 잘한 점/,/## 🔧/p' | head -n -1 | tail -n +2)

    local improvements
    improvements=$(echo "$content" | sed -n '/## 🔧 개선할 점/,/## 💡/p' | head -n -1 | tail -n +2)

    # JSON 이스케이프 함수
    json_escape() {
        echo "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null | sed 's/^"//;s/"$//' || echo "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\n/\\n/g'
    }

    # Block Kit JSON 생성
    cat << EOF
{
    "channel": "${SLACK_CHANNEL}",
    "username": "${SLACK_USERNAME}",
    "icon_emoji": "${SLACK_ICON_EMOJI}",
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📝 ${title}",
                "emoji": true
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📋 작업 요약*\n$(json_escape "$summary")"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*✅ 잘한 점*\n$(json_escape "$good_points")"
                },
                {
                    "type": "mrkdwn",
                    "text": "*🔧 개선할 점*\n$(json_escape "$improvements")"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "자동 생성됨 | $(date '+%Y-%m-%d %H:%M:%S')"
                }
            ]
        }
    ]
}
EOF
}

# 간단한 텍스트 형식으로 전송
create_simple_message() {
    local file_path=$1
    local content
    content=$(cat "$file_path")

    # JSON 이스케이프
    local escaped_content
    escaped_content=$(echo "$content" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo "\"$content\"")

    cat << EOF
{
    "channel": "${SLACK_CHANNEL}",
    "username": "${SLACK_USERNAME}",
    "icon_emoji": "${SLACK_ICON_EMOJI}",
    "text": ${escaped_content}
}
EOF
}

send_to_slack() {
    local payload=$1

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$SLACK_WEBHOOK_URL")

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]]; then
        log_info "Slack 전송 성공"
        return 0
    else
        log_error "Slack 전송 실패 (HTTP $http_code): $body"
        return 1
    fi
}

# ==================== 메인 ====================

main() {
    local worklog_file="${1:-}"
    local format="${2:-simple}"  # simple 또는 blocks

    if [[ -z "$worklog_file" ]]; then
        log_error "사용법: $0 <worklog_file> [simple|blocks]"
        exit 1
    fi

    if [[ ! -f "$worklog_file" ]]; then
        log_error "파일을 찾을 수 없습니다: $worklog_file"
        exit 1
    fi

    log_info "Slack 전송 시작"
    log_info "대상 파일: $worklog_file"
    log_info "전송 형식: $format"

    # 요구사항 확인
    check_requirements

    # 메시지 생성
    local payload
    if [[ "$format" == "blocks" ]]; then
        payload=$(create_slack_blocks "$worklog_file")
    else
        payload=$(create_simple_message "$worklog_file")
    fi

    # Slack 전송
    if send_to_slack "$payload"; then
        log_info "업무일지가 Slack으로 전송되었습니다."
    else
        log_error "Slack 전송에 실패했습니다."
        exit 1
    fi
}

# 스크립트 직접 실행 시
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
