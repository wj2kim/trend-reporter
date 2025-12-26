"""에펨코리아 데이터 수집기"""

import os
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from dataclasses import dataclass

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


@dataclass
class FMPost:
    """에펨코리아 게시글 데이터"""
    id: str
    title: str
    url: str
    hit: int
    recommend: int
    comment_count: int


class FMKoreaCollector:
    """에펨코리아 인기글 수집"""

    BASE_URL = "https://www.fmkorea.com"

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.cache = cache

    def collect_posts(self, limit: int = 20) -> List[FMPost]:
        """베스트 인기글 수집"""
        posts = []

        try:
            # 포텐 터진 게시물
            resp = self.session.get(
                f"{self.BASE_URL}/index.php?mid=best",
                timeout=15
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.li'):
                try:
                    title_elem = item.select_one('.title a')
                    if not title_elem:
                        continue

                    # 제목에서 말머리 제거
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get('href', '')

                    # 게시글 ID 추출
                    match = re.search(r'/(\d+)', href)
                    if not match:
                        continue
                    post_id = match.group(1)

                    cache_id = f"fm_{post_id}"
                    if self.cache and self.cache.is_seen(cache_id):
                        continue

                    # 조회수
                    hit = 0
                    hit_elem = item.select_one('.count')
                    if hit_elem:
                        hit_text = hit_elem.get_text(strip=True).replace(',', '')
                        hit = int(hit_text) if hit_text.isdigit() else 0

                    # 추천수
                    recommend = 0
                    rec_elem = item.select_one('.votes')
                    if rec_elem:
                        rec_text = rec_elem.get_text(strip=True).replace(',', '')
                        recommend = int(rec_text) if rec_text.lstrip('-').isdigit() else 0

                    # 댓글수
                    comment_count = 0
                    comment_elem = item.select_one('.comment_count')
                    if comment_elem:
                        comment_text = comment_elem.get_text(strip=True)
                        comment_count = int(comment_text) if comment_text.isdigit() else 0

                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

                    posts.append(FMPost(
                        id=post_id,
                        title=title,
                        url=full_url,
                        hit=hit,
                        recommend=recommend,
                        comment_count=comment_count
                    ))

                    if self.cache:
                        self.cache.mark_seen(cache_id)

                    if len(posts) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[FMKorea] 수집 실패: {e}")

        print(f"[FMKorea] {len(posts)}개 게시글 수집")
        return posts

    def format_for_analysis(self, posts: List[FMPost]) -> str:
        """분석용 텍스트 포맷"""
        if not posts:
            return "[에펨코리아] 새로운 게시글 없음\n"

        output = ["\n## 에펨코리아 (FMKorea)\n"]
        for i, post in enumerate(posts[:15], 1):
            output.append(
                f"{i}. {post.title}\n"
                f"   조회: {post.hit} | 추천: {post.recommend} | 댓글: {post.comment_count}\n"
                f"   URL: {post.url}\n"
            )
        return "\n".join(output)
