"""RSS 피드 수집기"""

import os
import hashlib
import feedparser
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from time import mktime

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


@dataclass
class RSSItem:
    """RSS 피드 항목 데이터"""
    id: str
    title: str
    url: str
    source: str
    category: str
    published: datetime
    summary: str = ""


class RSSCollector:
    """RSS 피드를 수집하는 클래스"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.cache = cache

    def _generate_id(self, url: str, title: str) -> str:
        """URL과 제목으로 고유 ID 생성"""
        content = f"{url}:{title}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def collect_feed(
        self,
        feed_url: str,
        feed_name: str,
        category: str,
        limit: int = 10
    ) -> List[RSSItem]:
        """단일 RSS 피드에서 항목 수집"""
        items = []

        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:limit * 2]:  # 캐시 고려
                url = entry.get("link", "")
                title = entry.get("title", "")

                # ID 생성
                item_id = f"rss_{self._generate_id(url, title)}"

                # 캐시된 항목 스킵
                if self.cache and self.cache.is_seen(item_id):
                    continue

                # 게시 시간 파싱
                published = datetime.now()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime.fromtimestamp(mktime(entry.published_parsed))
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime.fromtimestamp(mktime(entry.updated_parsed))

                # 요약 추출
                summary = ""
                if hasattr(entry, "summary"):
                    # HTML 태그 간단히 제거
                    summary = entry.summary
                    import re
                    summary = re.sub(r'<[^>]+>', '', summary)[:300]

                items.append(RSSItem(
                    id=item_id,
                    title=title,
                    url=url,
                    source=feed_name,
                    category=category,
                    published=published,
                    summary=summary
                ))

                # 캐시에 추가
                if self.cache:
                    self.cache.mark_seen(item_id)

                if len(items) >= limit:
                    break

        except Exception as e:
            print(f"[RSS] {feed_name} 수집 실패: {e}")

        return items

    def collect_all(
        self,
        feeds_config: List[Dict],
        items_per_feed: int = 10
    ) -> Dict[str, List[RSSItem]]:
        """모든 RSS 피드에서 카테고리별로 수집"""
        results = {}

        for feed in feeds_config:
            name = feed.get("name", "Unknown")
            url = feed.get("url", "")
            category = feed.get("category", "general")

            if not url:
                continue

            items = self.collect_feed(url, name, category, items_per_feed)
            print(f"[RSS] {name}: {len(items)}개 새 항목")

            if category not in results:
                results[category] = []
            results[category].extend(items)

        # 각 카테고리 시간순 정렬
        for category in results:
            results[category].sort(key=lambda x: x.published, reverse=True)

        return results

    def format_for_analysis(self, data: Dict[str, List[RSSItem]]) -> str:
        """분석을 위한 텍스트 포맷"""
        output = []
        total_items = 0

        for category, items in data.items():
            if not items:
                continue

            output.append(f"\n## RSS - {category.upper()}\n")
            for i, item in enumerate(items[:15], 1):
                output.append(
                    f"{i}. [{item.source}] {item.title}\n"
                    f"   URL: {item.url}\n"
                )
                if item.summary:
                    output.append(f"   요약: {item.summary[:150]}...\n")
                total_items += 1

        if total_items == 0:
            return "[RSS] 새로운 항목 없음\n"

        return "\n".join(output)
