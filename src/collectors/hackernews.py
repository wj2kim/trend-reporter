"""Hacker News 데이터 수집기"""

import os
import requests
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


@dataclass
class HNStory:
    """Hacker News 스토리 데이터"""
    id: int
    title: str
    url: str
    score: int
    num_comments: int
    author: str
    created_utc: datetime


class HackerNewsCollector:
    """Hacker News API를 사용하여 스토리를 수집하는 클래스"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.cache = cache

    def _fetch_item(self, item_id: int) -> Optional[dict]:
        """단일 아이템 가져오기"""
        try:
            resp = self.session.get(f"{HN_API_BASE}/item/{item_id}.json", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def _fetch_story_ids(self, endpoint: str, limit: int) -> List[int]:
        """스토리 ID 목록 가져오기"""
        try:
            resp = self.session.get(f"{HN_API_BASE}/{endpoint}.json", timeout=10)
            resp.raise_for_status()
            return resp.json()[:limit * 2]  # 캐시 고려해 더 가져옴
        except Exception as e:
            print(f"[HN] {endpoint} ID 목록 가져오기 실패: {e}")
            return []

    def collect_stories(
        self,
        story_type: str = "top",
        limit: int = 30
    ) -> List[HNStory]:
        """스토리 수집 (top, best, new)"""
        endpoint = f"{story_type}stories"
        story_ids = self._fetch_story_ids(endpoint, limit)

        stories = []

        # 병렬로 스토리 가져오기
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {
                executor.submit(self._fetch_item, sid): sid
                for sid in story_ids
            }

            for future in as_completed(future_to_id):
                item = future.result()
                if not item or item.get("type") != "story":
                    continue

                # 캐시된 스토리 스킵
                story_id = f"hn_{item['id']}"
                if self.cache and self.cache.is_seen(story_id):
                    continue

                # URL이 없는 Ask HN 등도 포함
                url = item.get("url", f"https://news.ycombinator.com/item?id={item['id']}")

                stories.append(HNStory(
                    id=item["id"],
                    title=item.get("title", ""),
                    url=url,
                    score=item.get("score", 0),
                    num_comments=item.get("descendants", 0),
                    author=item.get("by", "unknown"),
                    created_utc=datetime.fromtimestamp(item.get("time", 0))
                ))

                # 캐시에 추가
                if self.cache:
                    self.cache.mark_seen(story_id)

                if len(stories) >= limit:
                    break

        # 점수 기준 정렬
        stories.sort(key=lambda x: x.score, reverse=True)
        return stories

    def collect_all(self, top_limit: int = 30, best_limit: int = 20) -> dict:
        """top과 best 스토리 모두 수집"""
        results = {
            "top": self.collect_stories("top", top_limit),
            "best": self.collect_stories("best", best_limit)
        }

        # 중복 제거 (best에서 top에 있는 것 제외)
        top_ids = {s.id for s in results["top"]}
        results["best"] = [s for s in results["best"] if s.id not in top_ids]

        total = len(results["top"]) + len(results["best"])
        print(f"[HN] 총 {total}개 새 스토리 수집")

        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석을 위한 텍스트 포맷"""
        output = ["\n## Hacker News\n"]

        all_stories = data.get("top", []) + data.get("best", [])
        all_stories.sort(key=lambda x: x.score, reverse=True)

        if not all_stories:
            return "[HN] 새로운 스토리 없음\n"

        for i, story in enumerate(all_stories[:30], 1):
            output.append(
                f"{i}. {story.title}\n"
                f"   Score: {story.score} | Comments: {story.num_comments}\n"
                f"   URL: {story.url}\n"
            )

        return "\n".join(output)
