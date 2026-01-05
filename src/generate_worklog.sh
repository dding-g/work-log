#!/bin/bash
#
# 일일 업무일지 생성 스크립트
# Git 커밋을 분석하여 Markdown 업무일지를 자동 생성합니다.
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

# 기본값 설정
TIMEZONE="${TIMEZONE:-Asia/Seoul}"
WORKLOG_DIR="${WORKLOG_DIR:-${PROJECT_ROOT}/worklog}"
TARGET_REPO="${TARGET_REPO:-$(pwd)}"
LANGUAGE="${LANGUAGE:-ko}"

# ==================== 함수 ====================

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

get_yesterday_date() {
    TZ="$TIMEZONE" date -d "yesterday" +%Y-%m-%d 2>/dev/null || \
    TZ="$TIMEZONE" date -v-1d +%Y-%m-%d 2>/dev/null
}

get_day_of_week() {
    local date=$1
    local day_num
    day_num=$(TZ="$TIMEZONE" date -d "$date" +%u 2>/dev/null || \
              TZ="$TIMEZONE" date -j -f "%Y-%m-%d" "$date" +%u 2>/dev/null)

    local days_ko=("" "월요일" "화요일" "수요일" "목요일" "금요일" "토요일" "일요일")
    local days_en=("" "Monday" "Tuesday" "Wednesday" "Thursday" "Friday" "Saturday" "Sunday")

    if [[ "$LANGUAGE" == "ko" ]]; then
        echo "${days_ko[$day_num]}"
    else
        echo "${days_en[$day_num]}"
    fi
}

check_git_repo() {
    if ! git -C "$TARGET_REPO" rev-parse --git-dir > /dev/null 2>&1; then
        log_error "지정된 경로가 Git 저장소가 아닙니다: $TARGET_REPO"
        exit 1
    fi
}

get_repo_name() {
    basename "$(git -C "$TARGET_REPO" rev-parse --show-toplevel)"
}

get_my_email() {
    git -C "$TARGET_REPO" config user.email
}

get_commits() {
    local target_date=$1
    local my_email
    my_email=$(get_my_email)

    git -C "$TARGET_REPO" log \
        --author="$my_email" \
        --after="$target_date 00:00:00" \
        --before="$target_date 23:59:59" \
        --pretty=format:"%h|%s|%b" \
        --no-merges 2>/dev/null || echo ""
}

get_commit_stats() {
    local hash=$1
    git -C "$TARGET_REPO" show "$hash" --shortstat --format="" 2>/dev/null | tail -1
}

get_commit_files() {
    local hash=$1
    git -C "$TARGET_REPO" show "$hash" --stat --format="" 2>/dev/null
}

analyze_commit_type() {
    local subject=$1

    if [[ "$subject" =~ ^feat(\(.+\))?:|^feature ]]; then
        echo "feat"
    elif [[ "$subject" =~ ^fix(\(.+\))?:|^bugfix|^hotfix ]]; then
        echo "fix"
    elif [[ "$subject" =~ ^refactor(\(.+\))?: ]]; then
        echo "refactor"
    elif [[ "$subject" =~ ^docs(\(.+\))?: ]]; then
        echo "docs"
    elif [[ "$subject" =~ ^test(\(.+\))?: ]]; then
        echo "test"
    elif [[ "$subject" =~ ^chore(\(.+\))?: ]]; then
        echo "chore"
    elif [[ "$subject" =~ ^style(\(.+\))?: ]]; then
        echo "style"
    elif [[ "$subject" =~ ^perf(\(.+\))?: ]]; then
        echo "perf"
    elif [[ "$subject" =~ ^ci(\(.+\))?: ]]; then
        echo "ci"
    else
        echo "other"
    fi
}

evaluate_commit_quality() {
    local hash=$1
    local subject=$2
    local stats=$3
    local good_points=()
    local bad_points=()

    # 파일 수 체크
    local file_count
    file_count=$(git -C "$TARGET_REPO" show "$hash" --stat --format="" 2>/dev/null | grep -c '|' || echo "0")

    # 변경 라인 수 추출
    local insertions=0
    local deletions=0
    if [[ "$stats" =~ ([0-9]+)\ insertion ]]; then
        insertions="${BASH_REMATCH[1]}"
    fi
    if [[ "$stats" =~ ([0-9]+)\ deletion ]]; then
        deletions="${BASH_REMATCH[1]}"
    fi
    local total_changes=$((insertions + deletions))

    # 좋은 점 평가
    if [[ $file_count -le 5 ]]; then
        good_points+=("작고 집중된 커밋 (파일 $file_count개)")
    fi

    if [[ $total_changes -le 100 ]]; then
        good_points+=("적절한 변경 크기 (+$insertions/-$deletions)")
    fi

    if [[ "$subject" =~ ^(feat|fix|refactor|docs|test|chore|style|perf|ci)\(.+\): ]]; then
        good_points+=("컨벤션을 따르는 커밋 메시지")
    fi

    # 개선점 평가
    if [[ $file_count -gt 10 ]]; then
        bad_points+=("너무 많은 파일 변경 ($file_count개) - 커밋 분리 고려")
    fi

    if [[ $total_changes -gt 300 ]]; then
        bad_points+=("큰 변경 사항 (+$insertions/-$deletions) - God commit 가능성")
    fi

    if [[ "$subject" =~ ^(fix|update|change|modify)$ ]] || [[ ${#subject} -lt 10 ]]; then
        bad_points+=("모호한 커밋 메시지 - 더 구체적으로 작성 필요")
    fi

    # 디버깅 코드 체크
    if git -C "$TARGET_REPO" show "$hash" 2>/dev/null | grep -qE "console\.(log|debug)|print\(|debugger"; then
        bad_points+=("디버깅 코드 포함 가능성")
    fi

    echo "GOOD:${good_points[*]:-없음}"
    echo "BAD:${bad_points[*]:-없음}"
}

generate_worklog() {
    local target_date=$1
    local day_of_week
    day_of_week=$(get_day_of_week "$target_date")
    local repo_name
    repo_name=$(get_repo_name)
    local output_file="${WORKLOG_DIR}/${target_date}.md"

    # 출력 디렉토리 생성
    mkdir -p "$WORKLOG_DIR"

    # 커밋 수집
    local commits
    commits=$(get_commits "$target_date")

    # 커밋이 없는 경우
    if [[ -z "$commits" ]]; then
        cat > "$output_file" << EOF
# 업무일지 - ${target_date} (${day_of_week})

> 자동 생성됨 | 저장소: ${repo_name}

## 📋 작업 요약

오늘은 커밋이 없습니다.

---
*Generated by Work-Log Automation at $(date '+%Y-%m-%d %H:%M:%S')*
EOF
        log_info "커밋 없음 - 기본 템플릿 생성: $output_file"
        echo "$output_file"
        return
    fi

    # 커밋 분석
    local feat_commits=()
    local fix_commits=()
    local other_commits=()
    local total_insertions=0
    local total_deletions=0
    local total_files=0
    local all_good_points=()
    local all_bad_points=()
    local commit_count=0

    while IFS='|' read -r hash subject body; do
        [[ -z "$hash" ]] && continue
        commit_count=$((commit_count + 1))

        local commit_type
        commit_type=$(analyze_commit_type "$subject")
        local stats
        stats=$(get_commit_stats "$hash")

        # 통계 수집
        if [[ "$stats" =~ ([0-9]+)\ insertion ]]; then
            total_insertions=$((total_insertions + ${BASH_REMATCH[1]}))
        fi
        if [[ "$stats" =~ ([0-9]+)\ deletion ]]; then
            total_deletions=$((total_deletions + ${BASH_REMATCH[1]}))
        fi
        if [[ "$stats" =~ ([0-9]+)\ file ]]; then
            total_files=$((total_files + ${BASH_REMATCH[1]}))
        fi

        # 타입별 분류
        local commit_entry="- \`${hash}\` ${subject}"
        case "$commit_type" in
            feat)
                feat_commits+=("$commit_entry")
                ;;
            fix)
                fix_commits+=("$commit_entry")
                ;;
            *)
                other_commits+=("$commit_entry")
                ;;
        esac

        # 품질 평가
        local evaluation
        evaluation=$(evaluate_commit_quality "$hash" "$subject" "$stats")
        while IFS= read -r line; do
            if [[ "$line" == GOOD:* ]]; then
                local points="${line#GOOD:}"
                [[ "$points" != "없음" ]] && all_good_points+=("$points (${hash})")
            elif [[ "$line" == BAD:* ]]; then
                local points="${line#BAD:}"
                [[ "$points" != "없음" ]] && all_bad_points+=("$points (${hash})")
            fi
        done <<< "$evaluation"

    done <<< "$commits"

    # Markdown 생성
    cat > "$output_file" << EOF
# 업무일지 - ${target_date} (${day_of_week})

> 자동 생성됨 | 저장소: ${repo_name}

## 📋 작업 요약

EOF

    # 기능 개발 섹션
    if [[ ${#feat_commits[@]} -gt 0 ]]; then
        echo "### 기능 개발" >> "$output_file"
        printf '%s\n' "${feat_commits[@]}" >> "$output_file"
        echo "" >> "$output_file"
    fi

    # 버그 수정 섹션
    if [[ ${#fix_commits[@]} -gt 0 ]]; then
        echo "### 버그 수정" >> "$output_file"
        printf '%s\n' "${fix_commits[@]}" >> "$output_file"
        echo "" >> "$output_file"
    fi

    # 기타 작업 섹션
    if [[ ${#other_commits[@]} -gt 0 ]]; then
        echo "### 리팩토링/기타" >> "$output_file"
        printf '%s\n' "${other_commits[@]}" >> "$output_file"
        echo "" >> "$output_file"
    fi

    # 통계 섹션
    cat >> "$output_file" << EOF
## 📊 통계

| 항목 | 수치 |
|------|------|
| 커밋 수 | ${commit_count} |
| 변경 파일 | ${total_files} |
| 추가 라인 | +${total_insertions} |
| 삭제 라인 | -${total_deletions} |

EOF

    # 잘한 점 섹션
    echo "## ✅ 잘한 점" >> "$output_file"
    if [[ ${#all_good_points[@]} -gt 0 ]]; then
        local i=1
        for point in "${all_good_points[@]:0:3}"; do
            echo "${i}. ${point}" >> "$output_file"
            i=$((i + 1))
        done
    else
        echo "- 특이사항 없음" >> "$output_file"
    fi
    echo "" >> "$output_file"

    # 개선할 점 섹션
    echo "## 🔧 개선할 점" >> "$output_file"
    if [[ ${#all_bad_points[@]} -gt 0 ]]; then
        local i=1
        for point in "${all_bad_points[@]:0:3}"; do
            echo "${i}. ${point}" >> "$output_file"
            i=$((i + 1))
        done
    else
        echo "- 특이사항 없음" >> "$output_file"
    fi
    echo "" >> "$output_file"

    # Follow-up 섹션
    cat >> "$output_file" << EOF
## 💡 Follow-up

- [ ] 코드 리뷰 반영사항 확인
- [ ] 테스트 커버리지 확인
- [ ] 문서 업데이트 필요 여부 검토

---
*Generated by Work-Log Automation at $(date '+%Y-%m-%d %H:%M:%S')*
EOF

    log_info "업무일지 생성 완료: $output_file"
    echo "$output_file"
}

# ==================== 메인 ====================

main() {
    local target_date="${1:-$(get_yesterday_date)}"

    log_info "업무일지 생성 시작"
    log_info "대상 날짜: $target_date"
    log_info "대상 저장소: $TARGET_REPO"

    # Git 저장소 확인
    check_git_repo

    # 업무일지 생성
    local output_file
    output_file=$(generate_worklog "$target_date")

    log_info "===== 생성된 업무일지 ====="
    cat "$output_file"
    log_info "=========================="

    # 파일 경로 반환 (Slack 스크립트에서 사용)
    echo "OUTPUT_FILE=$output_file"
}

# 스크립트 직접 실행 시
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
