"""Lobste.rs 데이터 수집기"""

import os
import requests
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


LOBSTERS_BASE = "https://lobste.rs"


@dataclass
class LobstersStory:
    """Lobste.rs 스토리 데이터"""
    id: str
    title: str
    url: str
    score: int
    comment_count: int
    tags: List[str]
    author: str
    created_at: datetime


class LobstersCollector:
    """Lobste.rs JSON API를 사용하여 스토리를 수집하는 클래스"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache

    def collect_stories(
        self,
        story_type: str = "hottest",
        limit: int = 30
    ) -> List[LobstersStory]:
        """스토리 수집 (hottest, newest, active)"""
        try:
            resp = self.session.get(
                f"{LOBSTERS_BASE}/{story_type}.json",
                timeout=15
            )
            resp.raise_for_status()
            stories_data = resp.json()
        except Exception as e:
            print(f"[Lobsters] {story_type} 수집 실패: {e}")
            return []

        stories = []
        for item in stories_data:
            story_id = f"lobsters_{item['short_id']}"

            # 캐시된 스토리 스킵
            if self.cache and self.cache.is_seen(story_id):
                continue

            try:
                created = datetime.fromisoformat(
                    item.get("created_at", "").replace("Z", "+00:00")
                )
            except:
                created = datetime.now()

            # URL이 없으면 Lobsters 페이지 사용
            url = item.get("url") or f"{LOBSTERS_BASE}/s/{item['short_id']}"

            stories.append(LobstersStory(
                id=item["short_id"],
                title=item.get("title", ""),
                url=url,
                score=item.get("score", 0),
                comment_count=item.get("comment_count", 0),
                tags=item.get("tags", []),
                author=item.get("submitter_user", "unknown"),
                created_at=created
            ))

            # 캐시에 추가
            if self.cache:
                self.cache.mark_seen(story_id)

            if len(stories) >= limit:
                break

        return stories

    def collect_all(
        self,
        hottest_limit: int = 25,
        newest_limit: int = 10
    ) -> dict:
        """hottest와 newest 스토리 수집"""
        results = {
            "hottest": self.collect_stories("hottest", hottest_limit),
            "newest": self.collect_stories("newest", newest_limit)
        }

        # newest에서 hottest에 있는 것 제외
        hottest_ids = {s.id for s in results["hottest"]}
        results["newest"] = [
            s for s in results["newest"] if s.id not in hottest_ids
        ]

        total = len(results["hottest"]) + len(results["newest"])
        print(f"[Lobsters] 총 {total}개 새 스토리 수집")

        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석을 위한 텍스트 포맷"""
        output = ["\n## Lobste.rs\n"]

        all_stories = data.get("hottest", []) + data.get("newest", [])
        all_stories.sort(key=lambda x: x.score, reverse=True)

        if not all_stories:
            return "[Lobsters] 새로운 스토리 없음\n"

        for i, story in enumerate(all_stories[:20], 1):
            tags_str = ", ".join(story.tags[:3]) if story.tags else "no tags"
            output.append(
                f"{i}. {story.title}\n"
                f"   Score: {story.score} | Comments: {story.comment_count} | "
                f"Tags: {tags_str}\n"
                f"   URL: {story.url}\n"
            )

        return "\n".join(output)
