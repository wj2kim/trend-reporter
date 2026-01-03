"""Google Trends 데이터 수집기"""

from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


@dataclass
class TrendingTopic:
    """트렌드 토픽 데이터"""
    title: str
    traffic: str  # 검색량 (예: "100K+")
    related_queries: List[str]


class GoogleTrendsCollector:
    """Google Trends 실시간 검색어 수집"""

    def __init__(self, geo: str = "KR", hl: str = "ko"):
        """
        Args:
            geo: 국가 코드 (KR=한국, US=미국, JP=일본)
            hl: 언어 코드
        """
        self.geo = geo
        self.hl = hl
        self.pytrends = None

        if PYTRENDS_AVAILABLE:
            self.pytrends = TrendReq(hl=hl, tz=540)  # KST = UTC+9 = 540분

    def collect_realtime_trends(self, limit: int = 10) -> List[TrendingTopic]:
        """실시간 인기 검색어 수집"""
        if not PYTRENDS_AVAILABLE or not self.pytrends:
            print("[Google Trends] pytrends 라이브러리가 설치되지 않음")
            return []

        topics = []
        try:
            # 실시간 트렌드 (trending_searches)
            trending_df = self.pytrends.trending_searches(pn=self.geo.lower())

            for idx, row in trending_df.head(limit).iterrows():
                topic_title = row[0] if isinstance(row, (list, tuple)) else str(row.values[0])
                topics.append(TrendingTopic(
                    title=topic_title,
                    traffic="",
                    related_queries=[]
                ))

            print(f"[Google Trends] {len(topics)}개 트렌드 수집")

        except Exception as e:
            print(f"[Google Trends] 실시간 트렌드 수집 실패: {e}")
            # 대안: 일별 트렌드 시도
            try:
                daily_df = self.pytrends.today_searches(pn=self.geo)
                for title in daily_df.head(limit):
                    topics.append(TrendingTopic(
                        title=title,
                        traffic="",
                        related_queries=[]
                    ))
                print(f"[Google Trends] {len(topics)}개 일별 트렌드 수집")
            except Exception as e2:
                print(f"[Google Trends] 일별 트렌드도 실패: {e2}")

        return topics

    def collect_related_queries(self, keyword: str, limit: int = 5) -> List[str]:
        """특정 키워드의 관련 검색어 수집"""
        if not PYTRENDS_AVAILABLE or not self.pytrends:
            return []

        try:
            self.pytrends.build_payload([keyword], geo=self.geo, timeframe='now 1-d')
            related = self.pytrends.related_queries()

            if keyword in related and related[keyword]['rising'] is not None:
                rising_df = related[keyword]['rising']
                return rising_df['query'].head(limit).tolist()
        except Exception as e:
            print(f"[Google Trends] 관련 검색어 수집 실패: {e}")

        return []

    def format_for_report(self, topics: List[TrendingTopic]) -> str:
        """리포트용 포맷"""
        if not topics:
            return "[Google Trends] 트렌드 데이터 없음\n"

        output = ["\n## Google Trends (한국 실시간)\n"]

        for i, topic in enumerate(topics, 1):
            output.append(f"{i}. **{topic.title}**")
            if topic.traffic:
                output.append(f"   - 검색량: {topic.traffic}")
            if topic.related_queries:
                queries = ", ".join(topic.related_queries[:3])
                output.append(f"   - 관련: {queries}")

        output.append("")
        return "\n".join(output)
