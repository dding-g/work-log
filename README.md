# Work-Log Automation

Git 커밋을 분석하여 일일 업무일지를 자동 생성하고 Slack으로 전송하는 도구입니다.

## 기능

- Git 커밋 자동 수집 및 분석
- 커밋 타입별 분류 (feat, fix, refactor 등)
- 코드 품질 자동 평가 (잘한 점 / 개선점)
- Markdown 업무일지 생성
- Slack Webhook을 통한 알림

## 빠른 시작

### 1. 설정 파일 생성

```bash
cp config/config.env.example config/config.env
```

`config/config.env` 파일을 열어 Slack Webhook URL을 설정하세요:

```bash
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
SLACK_CHANNEL="#your-channel"
```

### 2. 실행

```bash
# 어제 업무일지 생성 + Slack 전송
./run.sh

# 업무일지만 생성 (Slack 전송 안 함)
./run.sh -g

# 특정 날짜 업무일지 생성
./run.sh -d 2024-01-15

# 특정 저장소 대상
./run.sh -r /path/to/your/repo
```

## 프로젝트 구조

```
work-log/
├── run.sh                    # 메인 실행 스크립트
├── src/
│   ├── generate_worklog.sh   # 업무일지 생성
│   └── slack_notify.sh       # Slack 알림
├── config/
│   ├── config.env            # 설정 파일 (gitignore)
│   └── config.env.example    # 설정 템플릿
├── worklog/                  # 생성된 업무일지
└── .github/workflows/
    └── daily-worklog.yml     # GitHub Actions
```

## 자동화 설정

### Cron (로컬)

```bash
# crontab -e
# 매일 오전 2시 실행
0 2 * * * cd /path/to/work-log && ./run.sh >> /var/log/worklog.log 2>&1
```

### GitHub Actions

1. Repository Settings > Secrets에서 다음 시크릿 추가:
   - `SLACK_WEBHOOK_URL`: Slack Webhook URL
   - `SLACK_CHANNEL` (선택): 채널 이름

2. 워크플로우가 매일 KST 오전 2시에 자동 실행됩니다.

3. 수동 실행: Actions 탭 > Daily Worklog > Run workflow

## 설정 옵션

| 환경 변수 | 설명 | 기본값 |
|-----------|------|--------|
| `TIMEZONE` | 타임존 | Asia/Seoul |
| `WORKLOG_DIR` | 업무일지 저장 경로 | ./worklog |
| `TARGET_REPO` | 대상 저장소 경로 | 현재 디렉토리 |
| `LANGUAGE` | 언어 (ko/en) | ko |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL | (필수) |
| `SLACK_CHANNEL` | Slack 채널 | #general |
| `SLACK_USERNAME` | 봇 이름 | Work-Log Bot |
| `SLACK_ICON_EMOJI` | 봇 이모지 | :memo: |

## 업무일지 형식

생성되는 업무일지 예시:

```markdown
# 업무일지 - 2024-01-15 (월요일)

## 📋 작업 요약

### 기능 개발
- `abc1234` feat: 사용자 인증 기능 추가

### 버그 수정
- `def5678` fix: 로그인 오류 수정

## 📊 통계
| 항목 | 수치 |
|------|------|
| 커밋 수 | 5 |
| 변경 파일 | 12 |
| 추가 라인 | +234 |
| 삭제 라인 | -56 |

## ✅ 잘한 점
1. 작고 집중된 커밋 (abc1234)
2. 컨벤션을 따르는 커밋 메시지

## 🔧 개선할 점
1. 큰 변경 사항 - God commit 가능성 (xyz9999)

## 💡 Follow-up
- [ ] 코드 리뷰 반영사항 확인
- [ ] 테스트 커버리지 확인
```

## Slack Webhook 설정

1. [Slack API](https://api.slack.com/apps)에서 새 앱 생성
2. "Incoming Webhooks" 활성화
3. 워크스페이스에 앱 설치
4. Webhook URL 복사하여 `config/config.env`에 설정

## 라이선스

MIT License
