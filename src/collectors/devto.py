"""DEV.to 데이터 수집기"""

import os
import time
import requests
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


DEVTO_API_BASE = "https://dev.to/api"


@dataclass
class DevToArticle:
    """DEV.to 아티클 데이터"""
    id: int
    title: str
    url: str
    description: str
    tags: List[str]
    positive_reactions_count: int
    comments_count: int
    author: str
    published_at: datetime


class DevToCollector:
    """DEV.to API를 사용하여 아티클을 수집하는 클래스"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache

    def collect_articles(
        self,
        tag: Optional[str] = None,
        top: str = "week",
        limit: int = 30
    ) -> List[DevToArticle]:
        """아티클 수집 (top: day, week, month, year, infinity)"""
        params = {
            "per_page": limit * 2,  # 캐시 고려
            "top": top
        }
        if tag:
            params["tag"] = tag

        try:
            resp = self.session.get(
                f"{DEVTO_API_BASE}/articles",
                params=params,
                timeout=15
            )
            resp.raise_for_status()
            articles_data = resp.json()
        except Exception as e:
            print(f"[DEV.to] 수집 실패: {e}")
            return []

        articles = []
        for item in articles_data:
            article_id = f"devto_{item['id']}"

            # 캐시된 아티클 스킵
            if self.cache and self.cache.is_seen(article_id):
                continue

            try:
                published = datetime.fromisoformat(
                    item.get("published_at", "").replace("Z", "+00:00")
                )
            except:
                published = datetime.now()

            articles.append(DevToArticle(
                id=item["id"],
                title=item.get("title", ""),
                url=item.get("url", ""),
                description=item.get("description", ""),
                tags=item.get("tag_list", []),
                positive_reactions_count=item.get("positive_reactions_count", 0),
                comments_count=item.get("comments_count", 0),
                author=item.get("user", {}).get("username", "unknown"),
                published_at=published
            ))

            # 캐시에 추가
            if self.cache:
                self.cache.mark_seen(article_id)

            if len(articles) >= limit:
                break

        return articles

    def collect_all(
        self,
        general_limit: int = 20,
        tags: Optional[List[str]] = None
    ) -> dict:
        """일반 + 태그별 아티클 수집"""
        results = {
            "general": self.collect_articles(limit=general_limit)
        }

        # 태그별 수집 (rate limit 방지를 위해 딜레이 추가)
        if tags:
            for tag in tags:
                time.sleep(1)  # 1초 딜레이
                tag_articles = self.collect_articles(tag=tag, limit=10)
                # 일반에서 이미 있는 것 제외
                general_ids = {a.id for a in results["general"]}
                tag_articles = [a for a in tag_articles if a.id not in general_ids]
                if tag_articles:
                    results[tag] = tag_articles

        total = sum(len(v) for v in results.values())
        print(f"[DEV.to] 총 {total}개 새 아티클 수집")

        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석을 위한 텍스트 포맷"""
        output = ["\n## DEV.to\n"]

        all_articles = []
        for articles in data.values():
            all_articles.extend(articles)

        # 중복 제거 후 반응 수로 정렬
        seen_ids = set()
        unique_articles = []
        for a in all_articles:
            if a.id not in seen_ids:
                seen_ids.add(a.id)
                unique_articles.append(a)

        unique_articles.sort(
            key=lambda x: x.positive_reactions_count,
            reverse=True
        )

        if not unique_articles:
            return "[DEV.to] 새로운 아티클 없음\n"

        for i, article in enumerate(unique_articles[:20], 1):
            tags_str = ", ".join(article.tags[:3]) if article.tags else "no tags"
            output.append(
                f"{i}. {article.title}\n"
                f"   ❤️ {article.positive_reactions_count} | "
                f"💬 {article.comments_count} | Tags: {tags_str}\n"
                f"   URL: {article.url}\n"
            )

        return "\n".join(output)
