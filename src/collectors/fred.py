"""FRED 경제지표 수집기"""

import os
from dataclasses import dataclass
from typing import List, Optional

import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


FRED_API_BASE = "https://api.stlouisfed.org/fred"


@dataclass
class FREDSeriesObservation:
    """FRED 시계열 최근 관측치"""
    series_id: str
    name: str
    date: str
    value: str
    previous_value: str
    category: str


class FREDCollector:
    """FRED API를 사용한 거시경제 지표 수집"""

    def __init__(self, cache: Optional[ContentCache] = None, api_key: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache
        self.api_key = api_key or os.getenv("FRED_API_KEY")

    def collect_series(self, series_cfg: dict) -> Optional[FREDSeriesObservation]:
        """단일 시계열의 최신 관측치 수집"""
        if not self.api_key:
            return None

        params = {
            "series_id": series_cfg["id"],
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 2,
        }

        try:
            resp = self.session.get(
                f"{FRED_API_BASE}/series/observations",
                params=params,
                timeout=20,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"[FRED] {series_cfg['id']} 수집 실패: {e}")
            return None

        observations = payload.get("observations", [])
        if not observations:
            return None

        latest = observations[0]
        previous = observations[1] if len(observations) > 1 else {"value": "N/A"}

        cache_id = f"fred_{series_cfg['id']}_{latest.get('date', '')}_{latest.get('value', '')}"
        if self.cache and self.cache.is_seen(cache_id):
            return None

        if self.cache:
            self.cache.mark_seen(cache_id)

        return FREDSeriesObservation(
            series_id=series_cfg["id"],
            name=series_cfg.get("name", series_cfg["id"]),
            date=latest.get("date", ""),
            value=latest.get("value", "N/A"),
            previous_value=previous.get("value", "N/A"),
            category=series_cfg.get("category", "macro"),
        )

    def collect_all(self, series: List[dict]) -> List[FREDSeriesObservation]:
        """설정된 FRED 시계열 수집"""
        if not self.api_key:
            print("[FRED] FRED_API_KEY가 없어 수집을 건너뜁니다.")
            return []

        results = []
        for series_cfg in series:
            item = self.collect_series(series_cfg)
            if item:
                results.append(item)

        print(f"[FRED] {len(results)}개 지표 수집")
        return results

    def format_for_analysis(self, data: List[FREDSeriesObservation]) -> str:
        """분석용 텍스트 포맷"""
        if not data:
            return "[FRED] 새로운 경제지표 없음\n"

        output = ["\n## FRED Macro Data\n"]
        for i, item in enumerate(data, 1):
            output.append(
                f"{i}. {item.name} ({item.series_id})\n"
                f"   Latest: {item.value} | Previous: {item.previous_value} | Date: {item.date}\n"
            )

        return "\n".join(output)
