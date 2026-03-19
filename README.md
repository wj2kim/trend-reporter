# Trend Reporter

> **사이트**: [https://wj2kim.github.io/trend-reporter/](https://wj2kim.github.io/trend-reporter/)

글로벌 트렌드(세계 정세, 주식, 기술, AI)를 15개 소스에서 수집하고 Gemini로 분석하여 GitHub Pages에 발행하는 자동화 시스템입니다.

## 기능

- **15개 소스 수집**: Hacker News, DEV.to, Lobste.rs, RSS, GitHub Trending, GitHub API, Claude Code 공식 채널, GeekNews, arXiv, OSV, GDELT, FRED, SEC, U.S. Treasury, Hugging Face
- **AI 분석**: Gemini 3 Flash Preview로 2개의 리포트 생성 (세계 정세 & 주식 / 개발 & AI)
- **자동 스케줄링**: GitHub Actions로 하루 2회 자동 실행 (09:00, 22:00 KST)
- **정적 발행**: GitHub Pages에 게시
- **중복 방지**: 이미 수집한 콘텐츠는 자동 스킵
- **데이터 영구 저장**: SQLite + FTS5 전문 검색

## 모니터링 카테고리

| 카테고리 | 소스 |
|---------|------|
| 세계 정세 | BBC, NPR, Al Jazeera, CNN, NYT, Washington Post |
| 미국 주식/경제 | Yahoo Finance, CNBC, MarketWatch, Seeking Alpha, Bloomberg, FRED, SEC, Treasury, Fed, ECB |
| 개발 트렌드 | Hacker News, DEV.to, Lobste.rs, GitHub Trending, GitHub API, GeekNews |
| AI | Hugging Face, OpenAI Blog, MIT Technology Review, arXiv |
| 보안 | OSV |
| Claude Code | npm, GitHub Releases, GitHub Issues |

## 설정 방법

### 1. 저장소 Fork 또는 Clone

```bash
git clone <your-repo-url>
cd trend-reporter
```

### 2. Gemini API 설정

1. https://aistudio.google.com/app/apikey 접속
2. API Keys 메뉴에서 새 키 생성
3. API 키 복사

### 3. GitHub Secrets 설정

Repository → Settings → Secrets and variables → Actions에서 추가:

| Secret Name | 값 |
|-------------|-----|
| `GEMINI_API_KEY` | Gemini API 키 |

선택:

| Secret Name | 값 |
|-------------|-----|
| `FRED_API_KEY` | FRED API 키 |
| `GH_TOKEN` | GitHub API 토큰 |
| `SEC_USER_AGENT` | SEC 요청용 User-Agent 문자열 |

### 4. 실행 테스트

GitHub → Actions → "Daily Trend Report" → "Run workflow"로 수동 실행

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 값 입력

# 실행
python src/main.py
```

## 리포트 구성

| 리포트 | 주요 섹션 |
|--------|----------|
| 세계 정세 & 주식 | 세계 정세, 시장 브리핑 (주식흐름·수혜주·이벤트), 핫 토픽, 인사이트 |
| 개발 & AI | AI/기술 트렌드, 개발 업데이트 (Vibe Coding·모델&API·개발 트렌드), 핫 레포, 인사이트 |

## 스케줄

한국 시간 기준:
- 오전 9시
- 오후 10시

## 비용

- **Hacker News API**: 무료
- **GitHub Actions**: 무료 (월 2000분)
- **Gemini API**: 호출량에 비례

## 커스터마이징

`config/sources.yaml` 파일을 수정하여:
- RSS 피드 추가
- 수집 개수 조정
- GitHub / arXiv / OSV / SEC / FRED / GDELT 쿼리 조정
- Claude Code / GeekNews 관련 수집 범위 조정

## 라이선스

MIT
