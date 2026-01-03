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

    def _get_base_rules(self, previous_titles: list = None) -> str:
        """공통 작성 규칙"""
        rules = """
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
        if previous_titles:
            rules += f"""
**[중복 방지] 이전 리포트에서 다룬 내용은 피하세요!**
아래는 최근 리포트 제목들입니다. 같은 주제를 반복하지 말고 새로운 내용에 집중하세요:
{chr(10).join(f'- {t}' for t in previous_titles)}

만약 새로운 내용이 없다면, 기존 내용의 "후속 전개"나 "새로운 관점"을 제시하세요.
"""
        return rules

    def analyze_world_market(self, collected_data: str, previous_titles: list = None) -> tuple:
        """세계 정세 & 주식 리포트 생성. (title, report) 튜플 반환"""
        now_kst = datetime.now(self.kst)
        timestamp = now_kst.strftime("%Y-%m-%d %H:%M KST")

        prompt = f"""당신은 글로벌 정세 및 금융 시장 분석 전문가입니다. 아래 수집된 데이터에서 **세계 정세와 주식/경제 관련 내용만** 추출하여 한국어로 리포트를 작성해주세요.

**중요: 리포트 맨 첫 줄에 반드시 아래 형식으로 제목과 키워드를 작성하세요:**
TITLE: [오늘의 가장 중요한 세계정세/주식 뉴스 한 줄 요약 (15자 이내)]
KEYWORDS: [핵심 키워드 2-3개, 쉼표로 구분]

예시:
TITLE: 연준 금리 동결, 증시 상승
KEYWORDS: 연준, 금리, FOMC

TITLE: 트럼프 관세 발표, 시장 급락
KEYWORDS: 트럼프, 관세, 무역전쟁

TITLE: 중동 긴장 고조, 유가 급등
KEYWORDS: 중동, 유가, 지정학

## 수집 시간
{timestamp}

## 수집된 데이터
{collected_data}

## 리포트 작성 지침
{self._get_base_rules(previous_titles)}

## 리포트 형식 (아래 형식을 정확히 따라주세요)

## 1. 세계 정세

• [핵심 이슈 요약 - 왜 중요한지]

• [두 번째 이슈]

• [세 번째 이슈]

### 시장 영향 분석

• [단기 영향 (1-2주)]: 어떤 섹터/종목이 즉각적으로 영향받을지, 상승/하락 방향과 근거

• [중기 영향 (1-3개월)]: 정책 변화, 기업 실적에 미칠 파급효과

• [투자 시사점]: 이 정세를 고려한 구체적인 투자 전략 제안


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


## 3. 오늘의 핫 3 토픽

**수집된 데이터에서 가장 주목할만한 세계 정세/경제 관련 토픽 3개를 선정하세요:**

### 토픽 1: [제목]
• [상세 설명 2-3문장]

### 토픽 2: [제목]
• [상세 설명 2-3문장]

### 토픽 3: [제목]
• [상세 설명 2-3문장]


## 4. 주식 커뮤니티 여론

**디시인사이드 주식갤러리, 뽐뿌 주식/코인 게시판에서 수집된 내용을 분석하세요:**

### a. 개인투자자 관심 종목
• [커뮤니티에서 자주 언급되는 종목과 그 이유]
• [매수/매도 의견 동향]

### b. 시장 심리
• [개미들의 전반적인 분위기 (낙관/비관/관망)]
• [주요 우려사항이나 기대감]

### c. 핫이슈
• [커뮤니티에서 논쟁 중인 주식/코인 관련 이슈]

(주식 커뮤니티 데이터가 없으면 "데이터 없음"으로 표시)


## 5. 인사이트

[세계 정세, 시장, 커뮤니티 여론을 종합한 2-3문장 인사이트]

---
세계 정세, 주식, 경제 관련 내용만 포함하세요. 개발/AI 관련 내용은 제외하세요.
"""

        return self._generate_report(prompt)

    def analyze_dev_ai(self, collected_data: str, previous_titles: list = None) -> tuple:
        """개발 & AI 리포트 생성. (title, report) 튜플 반환"""
        now_kst = datetime.now(self.kst)
        timestamp = now_kst.strftime("%Y-%m-%d %H:%M KST")

        prompt = f"""당신은 개발 및 AI 트렌드 분석 전문가입니다. 아래 수집된 데이터에서 **개발, 프로그래밍, AI 관련 내용만** 추출하여 한국어로 리포트를 작성해주세요.

**중요: 리포트 맨 첫 줄에 반드시 아래 형식으로 제목과 키워드를 작성하세요:**
TITLE: [오늘의 가장 중요한 개발/AI 뉴스 한 줄 요약 (15자 이내)]
KEYWORDS: [핵심 키워드 2-3개, 쉼표로 구분]

예시:
TITLE: GPT-5 발표, 코딩 혁신
KEYWORDS: GPT-5, OpenAI, AI

TITLE: React 19 출시, 성능 향상
KEYWORDS: React, 프론트엔드, 웹개발

TITLE: Claude 업데이트, MCP 지원
KEYWORDS: Claude, MCP, Anthropic

## 수집 시간
{timestamp}

## 수집된 데이터
{collected_data}

## 리포트 작성 지침
{self._get_base_rules(previous_titles)}

## 리포트 형식 (아래 형식을 정확히 따라주세요)

## 1. AI/기술 트렌드

### a. AI 모델 & 서비스
• [GPT, Gemini, Claude, Llama 등 주요 AI 모델 업데이트]
• [새로운 AI 서비스, 제품 출시]

### b. AI 기업 동향
• [OpenAI, Anthropic, Google, Meta 등 AI 기업 뉴스]
• [투자, 인수합병, 파트너십]

### c. AI 연구 & 기술
• [새로운 논문, 연구 결과]
• [기술 혁신, 벤치마크]

### d. AI 규제 & 정책
• [AI 관련 규제, 정책 변화]
• [윤리, 안전 관련 논의]


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


## 3. AI Coding Assistant

**Claude Code를 중심으로 AI 코딩 어시스턴트 관련 소식을 정리하세요:**

• [Claude Code 업데이트, 새로운 기능, 팁]

• [Cursor, Windsurf, GitHub Copilot 등 다른 AI 코딩 도구 소식]

• [AI 코딩 관련 튜토리얼, 활용 사례]

• [MCP(Model Context Protocol), 에이전트 관련 뉴스]


## 4. 주목할 만한 글

**AI/개발 분야 유명 인물들의 최신 글이나 트윗을 요약하세요:**

수집된 데이터에서 다음과 같은 인물들의 글을 찾아 요약하세요:
- AI 리더: Sam Altman, Dario Amodei, Demis Hassabis, Yann LeCun, Andrej Karpathy
- Anthropic/Claude: Amanda Askell, Alex Albert, Boris Power, Michael Gerstenhaber
- 개발자: DHH, ThePrimeagen, Theo, Fireship, Kent C. Dodds, Dan Abramov
- 기타 영향력 있는 기술 인물

### [저자명] - [글 제목/주제]
• 요약: [핵심 내용 2-3문장]
• 링크: [URL이 있으면 포함]

(해당 인물의 글이 없으면 이 섹션 생략)


## 5. 인사이트

[개발과 AI 트렌드를 종합한 2-3문장 인사이트]

---
개발, 프로그래밍, AI 관련 내용만 포함하세요. 세계 정세/주식 관련 내용은 제외하세요.
"""

        return self._generate_report(prompt)

    def analyze_community(self, collected_data: str, previous_titles: list = None) -> tuple:
        """한국 실시간 트렌드 리포트 생성. (title, keywords, report) 튜플 반환"""
        now_kst = datetime.now(self.kst)
        timestamp = now_kst.strftime("%Y-%m-%d %H:%M KST")

        prompt = f"""당신은 한국 실시간 트렌드 분석 전문가입니다. 아래 Google Trends 데이터를 분석하여 **한국에서 지금 가장 핫한 주제**를 리포트로 작성해주세요.

**중요: 리포트 맨 첫 줄에 반드시 아래 형식으로 제목과 키워드를 작성하세요:**
TITLE: [오늘 한국에서 가장 핫한 검색어/주제 한 줄 요약 (15자 이내)]
KEYWORDS: [핵심 키워드 2-3개, 쉼표로 구분]

예시:
TITLE: 연말 대상 논란 폭발
KEYWORDS: 연말대상, 시상식, 논란

TITLE: 신작 드라마 시청률 1위
KEYWORDS: 드라마, 시청률, 화제

## 수집 시간
{timestamp}

## 수집된 데이터
{collected_data}

## 리포트 작성 지침
{self._get_base_rules(previous_titles)}

**추가 지침:**
- 각 트렌드 검색어가 왜 화제인지 배경을 설명
- 관련 뉴스나 이슈가 있다면 함께 언급
- 민감한 정치/사회 이슈는 중립적으로 요약

## 리포트 형식 (아래 형식을 정확히 따라주세요)

## 1. 실시간 핫 키워드 TOP 5

**한국에서 지금 가장 많이 검색되는 주제:**

### 1. [검색어/주제]
• 배경: [왜 화제인지 2-3문장으로 설명]
• 관련 이슈: [관련 뉴스나 이벤트]

### 2. [검색어/주제]
• 배경: [설명]
• 관련 이슈: [관련 내용]

(3, 4, 5번도 동일 형식)


## 2. 트렌드 분석

### 카테고리별 트렌드
• **연예/엔터**: [관련 트렌드 요약]
• **스포츠**: [관련 트렌드 요약]
• **사회/정치**: [관련 트렌드 요약]
• **기타**: [기타 트렌드 요약]


## 3. 인사이트

[오늘 한국의 관심사와 전반적인 분위기를 2-3문장으로 요약]

---
Google Trends 데이터를 바탕으로 한국 사회의 관심사를 분석하세요.
"""

        return self._generate_report(prompt)

    def _generate_report(self, prompt: str) -> tuple:
        """Gemini API로 리포트 생성. (title, keywords, report) 튜플 반환"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            title, keywords, report = self._extract_title(text)
            return title, keywords, report
        except Exception as e:
            return "리포트", [], f"분석 실패: {e}"

    def _extract_title(self, text: str) -> tuple:
        """응답에서 제목, 키워드, 본문 분리. (title, keywords, report) 튜플 반환"""
        lines = text.strip().split('\n')
        title = "리포트"
        keywords = []
        report_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('TITLE:'):
                title = stripped.replace('TITLE:', '').strip()
            elif stripped.startswith('KEYWORDS:'):
                kw_str = stripped.replace('KEYWORDS:', '').strip()
                keywords = [k.strip() for k in kw_str.split(',') if k.strip()]
            else:
                report_lines.append(line)

        return title, keywords, '\n'.join(report_lines).strip()

    def create_report_header(self) -> str:
        """리포트 헤더 생성 (날짜 부분만)"""
        now_kst = datetime.now(self.kst)
        return now_kst.strftime("%Y-%m-%d %H:%M")
