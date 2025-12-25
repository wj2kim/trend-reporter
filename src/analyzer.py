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
        self.kst = pytz.timezone('Asia/Seoul')

    def _get_base_rules(self) -> str:
        """공통 작성 규칙"""
        return """
**[절대 규칙] 수집된 데이터에 없는 내용은 절대 작성하지 마세요!**
- 위 "수집된 데이터" 섹션에 언급되지 않은 뉴스, 인수합병, 제품 출시 등을 만들어내지 마세요
- 확인되지 않은 정보를 추측하거나 창작하지 마세요
- 수집된 데이터에서 찾을 수 없는 내용이면 해당 섹션에 "새로운 업데이트 없음"으로 표시하세요

1. **간결하게**: 각 섹션은 핵심만 3-5개 bullet point로 작성
2. **인사이트 중심**: 단순 나열이 아닌 의미있는 분석 제공
3. **한국 독자 관점**: 한국에 영향을 미칠 수 있는 내용 강조
4. **실용적**: 실질적으로 유용한 정보 위주
5. **가독성**: 각 항목 사이에 빈 줄을 넣어 읽기 쉽게 작성
6. **사실만 작성**: 수집된 데이터에 있는 내용만 리포트에 포함
"""

    def analyze_world_market(self, collected_data: str) -> tuple:
        """세계 정세 & 주식 리포트 생성. (title, report) 튜플 반환"""
        now_kst = datetime.now(self.kst)
        timestamp = now_kst.strftime("%Y-%m-%d %H:%M KST")

        prompt = f"""당신은 글로벌 정세 및 금융 시장 분석 전문가입니다. 아래 수집된 데이터에서 **세계 정세와 주식/경제 관련 내용만** 추출하여 한국어로 리포트를 작성해주세요.

**중요: 리포트 맨 첫 줄에 반드시 아래 형식으로 제목을 작성하세요:**
TITLE: [오늘의 가장 중요한 세계정세/주식 뉴스 한 줄 요약 (15자 이내)]

예시:
TITLE: 연준 금리 동결, 증시 상승
TITLE: 트럼프 관세 발표, 시장 급락
TITLE: 중동 긴장 고조, 유가 급등

## 수집 시간
{timestamp}

## 수집된 데이터
{collected_data}

## 리포트 작성 지침
{self._get_base_rules()}

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

### c. 오늘의 주식 이벤트

• [미국: FOMC, CPI, PPI, 고용지표, 실적발표 등]

• [글로벌: BOJ/ECB/기타 중앙은행 금리결정, 중국 경제지표, 유럽 지표 등]

• [이벤트가 없으면 "오늘 주요 이벤트 없음"으로 표시]

### d. Upcoming 이벤트

**[필수] 모든 이벤트에 정확한 날짜와 한국시간(KST)을 포함하세요!**

형식: • [M월 D일(요일) HH:MM KST] 이벤트명 - 설명

예시:
• [1월 10일(금) 22:30 KST] 미국 고용지표 발표 - 비농업 고용, 실업률
• [1월 15일(수) 22:30 KST] 미국 CPI 발표 - 소비자물가지수


## 3. 오늘의 핫 토픽

• [세계 정세/경제 관련 화제]


## 4. 인사이트

[세계 정세와 시장을 종합한 2-3문장 인사이트]

---
세계 정세, 주식, 경제 관련 내용만 포함하세요. 개발/AI 관련 내용은 제외하세요.
"""

        return self._generate_report(prompt)

    def analyze_dev_ai(self, collected_data: str) -> tuple:
        """개발 & AI 리포트 생성. (title, report) 튜플 반환"""
        now_kst = datetime.now(self.kst)
        timestamp = now_kst.strftime("%Y-%m-%d %H:%M KST")

        prompt = f"""당신은 개발 및 AI 트렌드 분석 전문가입니다. 아래 수집된 데이터에서 **개발, 프로그래밍, AI 관련 내용만** 추출하여 한국어로 리포트를 작성해주세요.

**중요: 리포트 맨 첫 줄에 반드시 아래 형식으로 제목을 작성하세요:**
TITLE: [오늘의 가장 중요한 개발/AI 뉴스 한 줄 요약 (15자 이내)]

예시:
TITLE: GPT-5 발표, 코딩 혁신
TITLE: React 19 출시, 성능 향상
TITLE: Claude 업데이트, MCP 지원

## 수집 시간
{timestamp}

## 수집된 데이터
{collected_data}

## 리포트 작성 지침
{self._get_base_rules()}

## 리포트 형식 (아래 형식을 정확히 따라주세요)

## 1. AI/기술 트렌드

• [주요 AI 발표, 새로운 기술, 업계 동향]

• [AI 모델 업데이트 (GPT, Gemini, Claude 등)]

• [AI 관련 주요 뉴스]


## 2. 개발 업데이트

### a. Vibe Coding

• [Claude Code, Cursor, Windsurf, Copilot 등 AI 코딩 에이전트 소식]

• [프롬프트 엔지니어링 팁, 생산성 향상 노하우]

### b. AI 모델 & API

• [AI 모델 업데이트, API 변경사항]

• [새로운 기능, 활용법]

### c. 개발 트렌드

• [프로그래밍 언어, 프레임워크, 라이브러리 관련 소식]

• [GitHub Trending, 인기 프로젝트]


## 3. 오늘의 핫 레포

• [GitHub에서 주목받는 프로젝트]

• [Hugging Face 인기 모델]


## 4. 인사이트

[개발과 AI 트렌드를 종합한 2-3문장 인사이트]

---
개발, 프로그래밍, AI 관련 내용만 포함하세요. 세계 정세/주식 관련 내용은 제외하세요.
"""

        return self._generate_report(prompt)

    def _generate_report(self, prompt: str) -> tuple:
        """Gemini API로 리포트 생성"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            title, report = self._extract_title(text)
            return title, report
        except Exception as e:
            return "리포트", f"분석 실패: {e}"

    def _extract_title(self, text: str) -> tuple:
        """응답에서 제목과 본문 분리"""
        lines = text.strip().split('\n')
        title = "리포트"
        report_lines = []

        for line in lines:
            if line.strip().startswith('TITLE:'):
                title = line.replace('TITLE:', '').strip()
            else:
                report_lines.append(line)

        return title, '\n'.join(report_lines).strip()

    def create_report_header(self) -> str:
        """리포트 헤더 생성 (날짜 부분만)"""
        now_kst = datetime.now(self.kst)
        return now_kst.strftime("%Y-%m-%d %H:%M")
