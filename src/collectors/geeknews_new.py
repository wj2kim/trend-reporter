"""GeekNews 새 소식 수집기"""

import re
from dataclasses import dataclass
from html import unescape
from typing import List, Optional

import requests

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


GEEKNEWS_NEW_URL = "https://news.hada.io/new"
TOPIC_SPLIT = "<div class='topic_row'>"


@dataclass
class GeekNewsItem:
    """GeekNews 최신 등록 항목"""
    topic_id: str
    title: str
    source_url: str
    source_domain: str
    summary: str
    points: int
    age_text: str
    comments_text: str
    discussion_url: str


class GeekNewsNewCollector:
    """GeekNews /new 페이지 수집기"""

    TITLE_PATTERN = re.compile(
        r"<div class=topictitle><a href='([^']+)'[^>]*><h1>(.*?)</h1></a>\s*<span class=topicurl>\((.*?)\)</span>",
        re.S,
    )
    DESC_PATTERN = re.compile(
        r"<div class='topicdesc'><a href='(topic\?id=\d+)'[^>]*>(.*?)</a></div>",
        re.S,
    )
    INFO_PATTERN = re.compile(
        r"<div class='topicinfo'><span id='tp(\d+)'>(\d+)</span> points by .*? ([^<]+?)<span .*?\|\s*<a href='([^']+)'",
        re.S,
    )

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        return " ".join(unescape(text).split())

    def collect_all(self, limit: int = 12) -> List[GeekNewsItem]:
        """GeekNews /new 최신 등록 항목 수집"""
        try:
            resp = self.session.get(GEEKNEWS_NEW_URL, timeout=20)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"[GeekNews] 수집 실패: {e}")
            return []

        items: List[GeekNewsItem] = []
        parts = html.split(TOPIC_SPLIT)[1:]

        for part in parts:
            title_match = self.TITLE_PATTERN.search(part)
            desc_match = self.DESC_PATTERN.search(part)
            info_match = self.INFO_PATTERN.search(part)
            if not title_match or not desc_match or not info_match:
                continue

            source_url, raw_title, domain = title_match.groups()
            discussion_path, raw_summary = desc_match.groups()
            topic_id, points, age_text, comments_path = info_match.groups()

            cache_id = f"geeknews_{topic_id}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            item = GeekNewsItem(
                topic_id=topic_id,
                title=self._clean_text(raw_title),
                source_url=source_url,
                source_domain=self._clean_text(domain),
                summary=self._clean_text(raw_summary)[:400],
                points=int(points),
                age_text=self._clean_text(age_text),
                comments_text="댓글과 토론" if "go=comments" not in comments_path else "댓글과 토론",
                discussion_url=f"https://news.hada.io/{discussion_path}",
            )
            items.append(item)

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(items) >= limit:
                break

        print(f"[GeekNews] {len(items)}개 새 항목 수집")
        return items

    def format_for_analysis(self, data: List[GeekNewsItem]) -> str:
        """분석용 텍스트 포맷"""
        if not data:
            return "[GeekNews] 새로운 항목 없음\n"

        output = ["\n## GeekNews New\n"]
        for i, item in enumerate(data, 1):
            output.append(
                f"{i}. [{item.source_domain}] {item.title}\n"
                f"   Points: {item.points} | Age: {item.age_text}\n"
                f"   Summary: {item.summary[:220]}\n"
                f"   Source: {item.source_url}\n"
                f"   Discussion: {item.discussion_url}\n"
            )

        return "\n".join(output)
