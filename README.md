# Trend Reporter

Reddit, Hacker News, RSS 피드에서 최신 트렌드를 수집하고 Claude AI로 분석하여 Slack으로 리포트를 전송하는 자동화 시스템입니다.

## 기능

- **다양한 소스 수집**: Reddit, Hacker News, RSS 피드
- **AI 분석**: Claude API로 트렌드 요약 및 인사이트 생성
- **자동 스케줄링**: GitHub Actions로 하루 6회 자동 실행
- **중복 방지**: 이미 수집한 콘텐츠는 자동 스킵

## 모니터링 카테고리

| 카테고리 | 소스 |
|---------|------|
| 세계 정세 | r/worldnews, r/geopolitics |
| 미국 주식 | r/stocks, r/wallstreetbets, r/investing |
| 기술 트렌드 | Hacker News, r/technology, r/programming |
| AI | r/MachineLearning, r/LocalLLaMA, r/artificial |
| 최신 트렌드 | Product Hunt, TechCrunch, The Verge |

## 설정 방법

### 1. 저장소 Fork 또는 Clone

```bash
git clone <your-repo-url>
cd trend-reporter
```

### 2. Reddit API 설정

1. https://www.reddit.com/prefs/apps 접속
2. "create another app..." 클릭
3. 타입: "script" 선택
4. 이름, 설명 입력 (예: TrendReporter)
5. redirect uri: http://localhost:8080 (사용하지 않음)
6. 생성 후 client_id (앱 이름 아래 문자열), client_secret 복사

### 3. Anthropic API 설정

1. https://console.anthropic.com 접속
2. API Keys 메뉴에서 새 키 생성
3. API 키 복사

### 4. Slack Webhook 설정

1. https://api.slack.com/apps 접속
2. "Create New App" → "From scratch"
3. 앱 이름 입력, 워크스페이스 선택
4. "Incoming Webhooks" → "Activate Incoming Webhooks" 활성화
5. "Add New Webhook to Workspace" → 채널 선택
6. Webhook URL 복사

### 5. GitHub Secrets 설정

Repository → Settings → Secrets and variables → Actions에서 추가:

| Secret Name | 값 |
|-------------|-----|
| `REDDIT_CLIENT_ID` | Reddit App Client ID |
| `REDDIT_CLIENT_SECRET` | Reddit App Secret |
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL |

### 6. 실행 테스트

GitHub → Actions → "Daily Trend Report" → "Run workflow"로 수동 실행

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt
pip install pytz

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 값 입력

# 실행
python src/main.py
```

## 스케줄

한국 시간 기준:
- 오전 9시
- 오후 9시, 10시, 11시
- 자정 12시
- 오전 1시

## 비용

- **Reddit API**: 무료
- **Hacker News API**: 무료
- **GitHub Actions**: 무료 (월 2000분)
- **Claude API**: 하루 약 $0.5~2 (6회 실행 기준)

## 커스터마이징

`config/sources.yaml` 파일을 수정하여:
- 모니터링할 subreddit 추가/제거
- RSS 피드 추가
- 수집 개수 조정

## 라이선스

MIT
