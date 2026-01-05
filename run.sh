#!/bin/bash
#
# Work-Log Automation 메인 실행 스크립트
# 업무일지 생성 후 Slack으로 전송합니다.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ==================== 함수 ====================

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

show_help() {
    cat << EOF
Work-Log Automation - 일일 업무일지 자동화 도구

사용법:
    $0 [옵션] [날짜]

옵션:
    -h, --help          이 도움말 표시
    -g, --generate      업무일지만 생성 (Slack 전송 안 함)
    -s, --slack         기존 업무일지를 Slack으로 전송
    -d, --date DATE     특정 날짜의 업무일지 처리 (YYYY-MM-DD)
    -r, --repo PATH     대상 저장소 경로 지정
    --dry-run           실제 전송 없이 테스트

예시:
    $0                          # 어제 업무일지 생성 + Slack 전송
    $0 -g                       # 어제 업무일지 생성만
    $0 -d 2024-01-15            # 특정 날짜 업무일지 생성 + Slack 전송
    $0 -s worklog/2024-01-15.md # 기존 파일 Slack 전송
    $0 -r /path/to/repo         # 특정 저장소 대상

EOF
}

# ==================== 메인 ====================

main() {
    local mode="full"  # full, generate, slack
    local target_date=""
    local target_repo=""
    local worklog_file=""
    local dry_run=false

    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -g|--generate)
                mode="generate"
                shift
                ;;
            -s|--slack)
                mode="slack"
                if [[ -n "${2:-}" && ! "$2" =~ ^- ]]; then
                    worklog_file="$2"
                    shift
                fi
                shift
                ;;
            -d|--date)
                target_date="$2"
                shift 2
                ;;
            -r|--repo)
                target_repo="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                # 날짜 형식인 경우
                if [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                    target_date="$1"
                else
                    log_error "알 수 없는 옵션: $1"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done

    log_info "Work-Log Automation 시작"
    log_info "실행 모드: $mode"

    # 저장소 경로 설정
    if [[ -n "$target_repo" ]]; then
        export TARGET_REPO="$target_repo"
    fi

    case $mode in
        full|generate)
            # 업무일지 생성
            log_info "업무일지 생성 중..."

            local generate_args=()
            [[ -n "$target_date" ]] && generate_args+=("$target_date")

            local output
            output=$("${SCRIPT_DIR}/src/generate_worklog.sh" "${generate_args[@]}")

            # 출력에서 파일 경로 추출
            worklog_file=$(echo "$output" | grep "^OUTPUT_FILE=" | cut -d= -f2)

            if [[ -z "$worklog_file" || ! -f "$worklog_file" ]]; then
                log_error "업무일지 생성 실패"
                exit 1
            fi

            log_info "업무일지 생성 완료: $worklog_file"

            # generate 모드면 여기서 종료
            if [[ "$mode" == "generate" ]]; then
                echo ""
                echo "===== 생성된 업무일지 ====="
                cat "$worklog_file"
                exit 0
            fi
            ;;
    esac

    # Slack 전송
    if [[ "$mode" == "full" || "$mode" == "slack" ]]; then
        if [[ -z "$worklog_file" ]]; then
            # 가장 최근 업무일지 찾기
            worklog_file=$(ls -t "${SCRIPT_DIR}/worklog/"*.md 2>/dev/null | head -1)
        fi

        if [[ -z "$worklog_file" || ! -f "$worklog_file" ]]; then
            log_error "전송할 업무일지를 찾을 수 없습니다."
            exit 1
        fi

        log_info "Slack 전송 중..."

        if [[ "$dry_run" == true ]]; then
            log_info "[DRY-RUN] Slack 전송 건너뜀"
            log_info "전송 대상 파일: $worklog_file"
        else
            "${SCRIPT_DIR}/src/slack_notify.sh" "$worklog_file"
        fi
    fi

    log_info "Work-Log Automation 완료"
}

main "$@"
