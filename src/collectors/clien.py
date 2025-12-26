"""클리앙 데이터 수집기"""

import os
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from dataclasses import dataclass

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


@dataclass
class ClienPost:
    """클리앙 게시글 데이터"""
    id: str
    title: str
    url: str
    hit: int
    comment_count: int
    category: str


class ClienCollector:
    """클리앙 인기글 수집"""

    BASE_URL = "https://www.clien.net"

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.cache = cache

    def collect_posts(self, limit: int = 20) -> List[ClienPost]:
        """인기글 수집"""
        posts = []

        try:
            # 모두의공원 인기글
            resp = self.session.get(
                f"{self.BASE_URL}/service/board/park",
                params={"od": "T31", "po": 0},  # 조회수 정렬
                timeout=15
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.list_item'):
                try:
                    title_elem = item.select_one('.subject_fixed')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = item.select_one('a.list_subject')
                    if not link:
                        continue

                    href = link.get('href', '')
                    post_id = href.split('/')[-1].split('?')[0]
                    cache_id = f"clien_{post_id}"

                    if self.cache and self.cache.is_seen(cache_id):
                        continue

                    # 조회수
                    hit_elem = item.select_one('.hit')
                    hit = 0
                    if hit_elem:
                        hit_text = hit_elem.get_text(strip=True)
                        hit = int(hit_text) if hit_text.isdigit() else 0

                    # 댓글수
                    comment_elem = item.select_one('.rSymph05')
                    comment_count = 0
                    if comment_elem:
                        comment_text = comment_elem.get_text(strip=True)
                        comment_count = int(comment_text) if comment_text.isdigit() else 0

                    posts.append(ClienPost(
                        id=post_id,
                        title=title,
                        url=f"{self.BASE_URL}{href}",
                        hit=hit,
                        comment_count=comment_count,
                        category="모두의공원"
                    ))

                    if self.cache:
                        self.cache.mark_seen(cache_id)

                    if len(posts) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[Clien] 수집 실패: {e}")

        print(f"[Clien] {len(posts)}개 게시글 수집")
        return posts

    def format_for_analysis(self, posts: List[ClienPost]) -> str:
        """분석용 텍스트 포맷"""
        if not posts:
            return "[클리앙] 새로운 게시글 없음\n"

        output = ["\n## 클리앙 (Clien)\n"]
        for i, post in enumerate(posts[:15], 1):
            output.append(
                f"{i}. {post.title}\n"
                f"   조회: {post.hit} | 댓글: {post.comment_count}\n"
                f"   URL: {post.url}\n"
            )
        return "\n".join(output)
