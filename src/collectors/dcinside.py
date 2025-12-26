"""디시인사이드 데이터 수집기"""

import os
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from dataclasses import dataclass

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


@dataclass
class DCPost:
    """디시인사이드 게시글 데이터"""
    id: str
    title: str
    url: str
    hit: int
    recommend: int
    gallery: str


class DCInsideCollector:
    """디시인사이드 인기글 수집"""

    BASE_URL = "https://gall.dcinside.com"

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.cache = cache

    def collect_posts(self, limit: int = 20) -> List[DCPost]:
        """힛갤 인기글 수집"""
        posts = []

        try:
            # 힛갤 (실시간 베스트)
            resp = self.session.get(
                f"{self.BASE_URL}/board/lists?id=hit",
                timeout=15
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.ub-content'):
                try:
                    # 공지 제외
                    if 'us-post' in item.get('class', []):
                        continue

                    title_elem = item.select_one('.gall_tit a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get('href', '')

                    # 게시글 ID 추출
                    post_id = item.get('data-no', '')
                    if not post_id:
                        continue

                    cache_id = f"dc_{post_id}"
                    if self.cache and self.cache.is_seen(cache_id):
                        continue

                    # 갤러리 이름
                    gall_elem = item.select_one('.gall_name')
                    gallery = gall_elem.get_text(strip=True) if gall_elem else ""

                    # 조회수
                    hit_elem = item.select_one('.gall_count')
                    hit = 0
                    if hit_elem:
                        hit_text = hit_elem.get_text(strip=True)
                        hit = int(hit_text) if hit_text.isdigit() else 0

                    # 추천수
                    rec_elem = item.select_one('.gall_recommend')
                    recommend = 0
                    if rec_elem:
                        rec_text = rec_elem.get_text(strip=True)
                        recommend = int(rec_text) if rec_text.isdigit() else 0

                    posts.append(DCPost(
                        id=post_id,
                        title=title,
                        url=f"{self.BASE_URL}{href}" if href.startswith('/') else href,
                        hit=hit,
                        recommend=recommend,
                        gallery=gallery
                    ))

                    if self.cache:
                        self.cache.mark_seen(cache_id)

                    if len(posts) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[DCInside] 수집 실패: {e}")

        print(f"[DCInside] {len(posts)}개 게시글 수집")
        return posts

    def format_for_analysis(self, posts: List[DCPost]) -> str:
        """분석용 텍스트 포맷"""
        if not posts:
            return "[디시인사이드] 새로운 게시글 없음\n"

        output = ["\n## 디시인사이드 (DCInside)\n"]
        for i, post in enumerate(posts[:15], 1):
            output.append(
                f"{i}. [{post.gallery}] {post.title}\n"
                f"   조회: {post.hit} | 추천: {post.recommend}\n"
                f"   URL: {post.url}\n"
            )
        return "\n".join(output)
