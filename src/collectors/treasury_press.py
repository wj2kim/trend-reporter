"""미국 재무부 보도자료 수집기"""

import re
from dataclasses import dataclass
from html import unescape
from typing import List, Optional

import requests

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


TREASURY_PRESS_URL = "https://home.treasury.gov/news/press-releases"
TREASURY_BASE_URL = "https://home.treasury.gov"


@dataclass
class TreasuryPressRelease:
    """재무부 보도자료 데이터"""
    date: str
    title: str
    url: str


class TreasuryPressCollector:
    """미국 재무부 보도자료 페이지 수집기"""

    ROW_PATTERN = re.compile(
        r'<time[^>]+datetime="([^"]+)"[^>]*>.*?</time>\s*<div class="news-title"><a href="(/news/press-releases/[^"]+)"[^>]*>(.*?)</a>',
        re.S,
    )

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache

    def collect_all(self, limit: int = 6) -> List[TreasuryPressRelease]:
        """재무부 보도자료 목록 수집"""
        try:
            resp = self.session.get(TREASURY_PRESS_URL, timeout=20)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"[Treasury] 수집 실패: {e}")
            return []

        items = []
        seen_urls = set()
        for date_str, href, raw_title in self.ROW_PATTERN.findall(html):
            if href in seen_urls:
                continue
            seen_urls.add(href)

            title = " ".join(unescape(re.sub(r"<[^>]+>", " ", raw_title)).split())
            url = f"{TREASURY_BASE_URL}{href}"
            cache_id = f"treasury_{href}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            items.append(TreasuryPressRelease(
                date=date_str,
                title=title,
                url=url,
            ))

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(items) >= limit:
                break

        print(f"[Treasury] {len(items)}개 보도자료 수집")
        return items

    def format_for_analysis(self, data: List[TreasuryPressRelease]) -> str:
        """분석용 텍스트 포맷"""
        if not data:
            return "[Treasury] 새로운 보도자료 없음\n"

        output = ["\n## U.S. Treasury Press Releases\n"]
        for i, item in enumerate(data, 1):
            output.append(
                f"{i}. {item.title}\n"
                f"   Date: {item.date}\n"
                f"   URL: {item.url}\n"
            )

        return "\n".join(output)
