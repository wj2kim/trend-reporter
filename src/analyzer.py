"""Google Gemini API를 사용한 트렌드 분석기"""

import os
import google.generativeai as genai
from datetime import datetime
import pytz


class TrendAnalyzer:
    """수집된 데이터를 Gemini API로 분석하는 클래스"""

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')  # 무료 tier

    def analyze(self, collected_data: str) -> str:
        """수집된 데이터를 분석하여 리포트 생성"""

        # 한국 시간
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        timestamp = now_kst.strftime("%Y-%m-%d %H:%M KST")

        prompt = f"""당신은 글로벌 트렌드 분석 전문가입니다. 아래 수집된 데이터를 분석하여 한국어로 간결한 리포트를 작성해주세요.

## 수집 시간
{timestamp}

## 수집된 데이터
{collected_data}

## 리포트 작성 지침
1. **간결하게**: 각 섹션은 핵심만 3-5개 bullet point로 작성
2. **인사이트 중심**: 단순 나열이 아닌 의미있는 분석 제공
3. **한국 독자 관점**: 한국에 영향을 미칠 수 있는 내용 강조
4. **실용적**: 투자, 기술 트렌드 등 실질적으로 유용한 정보 위주

## 리포트 형식

### 세계 정세
• [핵심 이슈 요약 - 왜 중요한지]

### 미국 주식/경제
• [시장 동향 및 주목할 종목/섹터]

### AI/기술 트렌드
• [주요 발표, 새로운 기술, 업계 동향]

### 오늘의 핫 토픽
• [가장 화제가 된 주제 1-2개]

### 인사이트
[전체 데이터를 종합한 2-3문장 인사이트. 앞으로의 방향성이나 주목할 점]

---
만약 특정 카테고리에 새로운 데이터가 없으면 "새로운 업데이트 없음"으로 표시하세요.
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"분석 실패: {e}"

    def create_report_header(self) -> str:
        """리포트 헤더 생성"""
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        return f"📊 트렌드 리포트 | {now_kst.strftime('%Y-%m-%d %H:%M')} KST"
