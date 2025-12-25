"""Google Gemini API를 사용한 트렌드 분석기"""

import os
import google.generativeai as genai
from datetime import datetime
import pytz


class TrendAnalyzer:
    """수집된 데이터를 Gemini API로 분석하는 클래스"""

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-3-flash-preview')

    def analyze(self, collected_data: str) -> tuple:
        """수집된 데이터를 분석하여 리포트 생성. (title, report) 튜플 반환"""

        # 한국 시간
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        timestamp = now_kst.strftime("%Y-%m-%d %H:%M KST")

        prompt = f"""당신은 글로벌 트렌드 분석 전문가입니다. 아래 수집된 데이터를 분석하여 한국어로 간결한 리포트를 작성해주세요.

**중요: 리포트 맨 첫 줄에 반드시 아래 형식으로 제목을 작성하세요:**
TITLE: [오늘의 가장 중요한 핵심 뉴스/트렌드 한 줄 요약 (15자 이내)]

예시:
TITLE: 연준 금리 동결, AI 반도체 급등
TITLE: 트럼프 관세 발표, 테슬라 신고가
TITLE: 엔비디아 실적 발표, 시장 관망세

## 수집 시간
{timestamp}

## 수집된 데이터
{collected_data}

## 리포트 작성 지침
1. **간결하게**: 각 섹션은 핵심만 3-5개 bullet point로 작성
2. **인사이트 중심**: 단순 나열이 아닌 의미있는 분석 제공
3. **한국 독자 관점**: 한국에 영향을 미칠 수 있는 내용 강조
4. **실용적**: 투자, 기술 트렌드 등 실질적으로 유용한 정보 위주
5. **가독성**: 각 항목 사이에 빈 줄을 넣어 읽기 쉽게 작성

## 리포트 형식 (아래 형식을 정확히 따라주세요)

## 1. 세계 정세

• [핵심 이슈 요약 - 왜 중요한지]

• [두 번째 이슈]

• [세 번째 이슈]


## 2. 시장 브리핑

### a. 오늘의 주식흐름 전망

• [미국 주식시장 방향성 전망 - 상승/하락/보합 예상 및 근거]

• [주목할 섹터와 이유]

### b. 오늘의 수혜주 분석

• [티커(종목명) - 수혜 예상 이유]

• [예: NVDA(엔비디아) - AI 반도체 수요 증가 수혜]

### c. 오늘의 주식 이벤트

• [미국: FOMC, CPI, PPI, 고용지표, 실적발표 등]

• [글로벌: BOJ/ECB/기타 중앙은행 금리결정, 중국 경제지표, 유럽 지표 등]

• [지정학적 이슈: 미중관계, 중동, 관세, 제재 등 시장 영향 이벤트]

• [이벤트가 없으면 "오늘 주요 이벤트 없음"으로 표시]

### d. Upcoming 이벤트

**[필수] 아래 형식을 정확히 따라 작성하세요. 날짜와 한국시간 없이 작성하면 안 됩니다!**

형식: • [M월 D일(요일) HH:MM KST] 이벤트명 - 설명

실제 예시 (이 형식 그대로 따라하세요):
• [1월 10일(금) 22:30 KST] 미국 고용지표 발표 - 비농업 고용, 실업률
• [1월 15일(수) 22:30 KST] 미국 CPI 발표 - 소비자물가지수
• [1월 29일(수) 04:00 KST] FOMC 금리결정 - 연준 통화정책 발표

위 형식처럼 반드시 [날짜 시간]을 맨 앞에 붙이세요. 시간을 모르면 날짜만이라도 포함하세요.


## 3. 오늘의 핫 토픽

• [가장 화제가 된 주제]

• [두 번째 화제]


## 4. 오늘의 AI/기술 트렌드

• [주요 발표, 새로운 기술, 업계 동향]

• [AI 관련 주요 뉴스]


## 5. 개발 업데이트

### a. Vibe Coding

• [Claude Code 업데이트, 새 기능, 활용 팁 (메인)]

• [Cursor, Windsurf, Copilot 등 AI 코딩 에이전트 소식]

• [Vibe Coding 워크플로우, 프롬프트 엔지니어링 팁]

• [AI 페어 프로그래밍 베스트 프랙티스, 생산성 향상 노하우]

### b. AI 모델 & API

• [GPT, Gemini, Grok, Claude 등 AI 모델 업데이트]

• [AI API 활용법, 새로운 기능 소개]

### c. 개발 트렌드

• [DEV.to, Hacker News 등에서 수집된 개발 관련 소식]

• [프로그래밍 언어, 프레임워크, 라이브러리 관련 소식]


## 6. 인사이트

[전체 데이터를 종합한 2-3문장 인사이트. 앞으로의 방향성이나 주목할 점]

---
만약 특정 카테고리에 새로운 데이터가 없으면 "새로운 업데이트 없음"으로 표시하세요.
주식 관련 분석은 수집된 데이터와 일반적인 시장 지식을 기반으로 작성하세요.
각 bullet point 사이에 빈 줄을 넣어 가독성을 높여주세요.
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text

            # 제목과 본문 분리
            title, report = self._extract_title(text)
            return title, report
        except Exception as e:
            return "트렌드 리포트", f"분석 실패: {e}"

    def _extract_title(self, text: str) -> tuple:
        """응답에서 제목과 본문 분리"""
        lines = text.strip().split('\n')
        title = "트렌드 리포트"  # 기본값
        report_lines = []

        for i, line in enumerate(lines):
            if line.strip().startswith('TITLE:'):
                title = line.replace('TITLE:', '').strip()
            else:
                report_lines.append(line)

        return title, '\n'.join(report_lines).strip()

    def create_report_header(self) -> str:
        """리포트 헤더 생성 (날짜 부분만)"""
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        return now_kst.strftime("%Y-%m-%d %H:%M")
