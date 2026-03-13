"""GDELT 문서 API 수집기"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


@dataclass
class GDELTArticle:
    """GDELT 기사 데이터"""
    title: str
    url: str
    source: str
    domain: str
    seendate: str
    category: str


class GDELTCollector:
    """GDELT DOC 2 API를 사용해 최근 기사 클러스터를 수집"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache

    def collect_query(
        self,
        query: str,
        category: str,
        max_records: int = 8,
        timespan: str = "24h"
    ) -> List[GDELTArticle]:
        """단일 GDELT 쿼리 실행"""
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records * 2,
            "timespan": timespan,
        }

        for attempt in range(2):
            try:
                resp = self.session.get(GDELT_API_URL, params=params, timeout=30)
                if resp.status_code == 429 and attempt == 0:
                    time.sleep(6)
                    continue
                resp.raise_for_status()
                payload = resp.json()
                break
            except Exception as e:
                if attempt == 0:
                    time.sleep(6)
                    continue
                print(f"[GDELT] 쿼리 실패: {e}")
                return []

        articles = []
        for item in payload.get("articles", []):
            url = item.get("url", "")
            title = item.get("title", "").strip()
            if not url or not title:
                continue

            cache_id = f"gdelt_{url}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            articles.append(GDELTArticle(
                title=title,
                url=url,
                source=item.get("sourceCommonName", ""),
                domain=item.get("domain", ""),
                seendate=item.get("seendate", ""),
                category=category,
            ))

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(articles) >= max_records:
                break

        return articles

    def collect_all(self, queries: List[dict], max_records: int = 8, timespan: str = "24h") -> dict:
        """쿼리 목록을 순차적으로 실행"""
        results = {}

        for index, query_cfg in enumerate(queries):
            category = query_cfg.get("category", query_cfg.get("name", "general"))
            query = query_cfg.get("query", "").strip()
            if not query:
                continue

            if index > 0:
                time.sleep(6)

            articles = self.collect_query(
                query=query,
                category=category,
                max_records=max_records,
                timespan=timespan,
            )
            results[category] = articles
            print(f"[GDELT] {category}: {len(articles)}개 기사 수집")

        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석용 텍스트 포맷"""
        output = []
        total = 0

        for category, articles in data.items():
            if not articles:
                continue

            output.append(f"\n## GDELT - {category.upper()}\n")
            for i, article in enumerate(articles[:10], 1):
                source = article.source or article.domain or "unknown"
                output.append(
                    f"{i}. [{source}] {article.title}\n"
                    f"   URL: {article.url}\n"
                )
                total += 1

        if total == 0:
            return "[GDELT] 새로운 기사 없음\n"

        return "\n".join(output)
