# Trend Reporter 프로젝트 컨텍스트

## 프로젝트 개요
글로벌 트렌드(세계 정세, 주식, 기술, AI)를 자동 수집하고 분석하여 Discord로 리포트를 전송하는 시스템.

## 아키텍처

```
[데이터 수집] → [Gemini 분석] → [Discord 전송]
                              → [GitHub Pages 저장]
     ↓
┌─────────────────────────────────────┐
│ Collectors (src/collectors/)        │
│ - HackerNews (기술 트렌드)           │
│ - DEV.to (개발자 커뮤니티)            │
│ - Lobste.rs (기술 뉴스)              │
│ - RSS (뉴스 매체 20개+)              │
│ - GitHub Trending (인기 레포)        │
│ - Hugging Face (AI 모델 트렌드)      │
│ - Reddit (비활성화 - API 승인 대기)   │
└─────────────────────────────────────┘
```

## 현재 설정

### Gemini 모델
- `gemini-3-flash-preview` (src/analyzer.py)

### 실행 스케줄 (GitHub Actions)
- KST 09:00, 22:00 (하루 2회)
- `.github/workflows/report.yml` 에서 cron 설정 확인

### 알림 & 배포
- Discord 웹훅 (src/notifier.py)
- GitHub Pages (src/publisher.py) - https://wj2kim.github.io/trend-reporter/

## 리포트 구조

**두 개의 리포트 생성:**

### 1. 세계 정세 & 주식 리포트 (Market)
```
1. 세계 정세
   - 글로벌 핵심 이슈
2. 시장 브리핑
   a. 오늘의 주식흐름 전망
   b. 오늘의 수혜주 분석
   c. 오늘의 주식 이벤트
   d. Upcoming 이벤트 (날짜/시간 포함)
3. 오늘의 핫 토픽
4. 인사이트
```

### 2. 개발 & AI 리포트 (Dev)
```
1. AI/기술 트렌드
2. 개발 업데이트
   a. Vibe Coding (AI 코딩 에이전트)
   b. AI 모델 & API
   c. 개발 트렌드
3. 오늘의 핫 레포
4. 인사이트
```

## 파일 구조

```
trend-reporter/
├── src/
│   ├── main.py              # 메인 실행
│   ├── analyzer.py          # Gemini 분석 (프롬프트 정의)
│   ├── notifier.py          # Discord 웹훅
│   ├── publisher.py         # GitHub Pages 저장
│   ├── cache.py             # 중복 방지 캐시
│   └── collectors/
│       ├── hackernews.py    # HN API
│       ├── devto.py         # DEV.to API
│       ├── lobsters.py      # Lobste.rs JSON
│       ├── rss.py           # RSS 피드
│       ├── github_trending.py # GitHub Trending
│       ├── huggingface.py   # Hugging Face API
│       └── reddit.py        # (비활성화)
├── docs/                    # GitHub Pages (자동 생성)
│   ├── index.html           # 리포트 목록
│   ├── reports.json         # 리포트 메타데이터
│   └── reports/             # 개별 리포트 HTML
├── config/
│   └── sources.yaml         # 수집 소스 설정
├── .github/workflows/       # GitHub Actions
└── cache/                   # 캐시 저장
```

## 환경 변수 (GitHub Secrets)

- `GEMINI_API_KEY` - Google Gemini API 키
- `DISCORD_WEBHOOK_URL` - Discord 웹훅 URL

## 변경 히스토리

### 2026-02-03
- **커뮤니티 트렌드 리포트 제거**
- Google Trends 수집 및 분석 코드 제거
- analyzer.py: `analyze_community()` 메소드 제거
- notifier.py: `send_community_report()` 메소드 제거
- main.py: 커뮤니티 수집 및 리포트 생성 로직 제거
- **실행 스케줄 변경**: 하루 3회 → 2회 (24:00 KST 제거)
- Gemini API 호출: 사이클당 3회 → 2회, 하루 총 9회 → 4회

### 2024-12-26 (v2)
- **두 개의 리포트로 분리**: 세계정세&주식 / 개발&AI
- analyzer.py: `analyze_world_market()`, `analyze_dev_ai()` 분리
- publisher.py: 카테고리별 저장 및 배지 표시
- notifier.py: 두 리포트 연속 전송 (다른 색상)
- 실행 스케줄 변경: 09:00, 22:00, 24:00 KST

### 2024-12-26 (v1)
- GitHub Pages 자동 배포 추가 (src/publisher.py)
- 리포트를 HTML로 변환하여 docs/ 폴더에 저장
- 워크플로우에서 자동으로 커밋 & 푸시

### 2024-12-19
- DEV.to, Lobste.rs collector 추가 (Reddit 대안)
- DEV.to API `top` 파라미터 제거 (빈 결과 반환 이슈)
- Lobste.rs `submitter_user` 필드 수정 (string 타입)

### 리포트 구조 개선
- "주식 빅뉴스" → "시장 브리핑" 으로 변경
- Upcoming 이벤트 섹션 추가
- 글로벌 이벤트 확장 (BOJ, ECB, 지정학)
- "개발 업데이트" 섹션 추가
  - "Claude Code" → "Vibe Coding" 으로 확장
  - AI 코딩 에이전트 전반 커버

### Gemini 모델 변경
- gemini-2.0-flash → gemini-3-flash-preview

## 알려진 이슈

1. **Reddit API** - 승인 대기 중, 현재 비활성화
2. **DEV.to Rate Limit** - 태그별 요청 시 1초 딜레이 추가됨

## 향후 계획 (미구현)

- [ ] 카카오톡 "나에게 보내기" 연동 (무료, OAuth 필요)
- [ ] 텔레그램 봇 연동

## 자주 사용하는 명령

```bash
# 워크플로우 수동 실행
~/bin/gh workflow run "Daily Trend Report" -R wj2kim/trend-reporter

# 실행 상태 확인
~/bin/gh run list -R wj2kim/trend-reporter --limit 3

# 로그 확인
~/bin/gh run view <RUN_ID> -R wj2kim/trend-reporter --log

# 캐시 삭제 (새로운 데이터 수집)
~/bin/gh cache delete --all -R wj2kim/trend-reporter
```
