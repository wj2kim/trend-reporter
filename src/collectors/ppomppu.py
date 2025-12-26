"""뽐뿌 데이터 수집기"""

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
class PpomppuPost:
    """뽐뿌 게시글 데이터"""
    id: str
    title: str
    url: str
    hit: int
    recommend: int
    comment_count: int
    category: str


class PpomppuCollector:
    """뽐뿌 인기글 수집"""

    BASE_URL = "https://www.ppomppu.co.kr"

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.cache = cache

    def collect_posts(self, limit: int = 20) -> List[PpomppuPost]:
        """핫게시판 인기글 수집"""
        posts = []

        try:
            # 핫게시판
            resp = self.session.get(
                f"{self.BASE_URL}/hot.php",
                timeout=15
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('tr.line'):
                try:
                    title_elem = item.select_one('.title a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get('href', '')

                    # 게시글 ID 추출
                    match = re.search(r'no=(\d+)', href)
                    if not match:
                        continue
                    post_id = match.group(1)

                    cache_id = f"ppomppu_{post_id}"
                    if self.cache and self.cache.is_seen(cache_id):
                        continue

                    # 카테고리
                    cat_elem = item.select_one('.exp')
                    category = cat_elem.get_text(strip=True) if cat_elem else ""

                    # 조회수
                    tds = item.select('td')
                    hit = 0
                    recommend = 0
                    comment_count = 0

                    if len(tds) >= 5:
                        # 조회수
                        hit_text = tds[-1].get_text(strip=True).replace(',', '')
                        hit = int(hit_text) if hit_text.isdigit() else 0

                        # 추천수
                        rec_text = tds[-2].get_text(strip=True).replace(',', '')
                        recommend = int(rec_text) if rec_text.lstrip('-').isdigit() else 0

                    # 댓글수
                    comment_elem = item.select_one('.list_comment2')
                    if comment_elem:
                        comment_text = comment_elem.get_text(strip=True)
                        match = re.search(r'\d+', comment_text)
                        if match:
                            comment_count = int(match.group())

                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

                    posts.append(PpomppuPost(
                        id=post_id,
                        title=title,
                        url=full_url,
                        hit=hit,
                        recommend=recommend,
                        comment_count=comment_count,
                        category=category
                    ))

                    if self.cache:
                        self.cache.mark_seen(cache_id)

                    if len(posts) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[Ppomppu] 수집 실패: {e}")

        print(f"[Ppomppu] {len(posts)}개 게시글 수집")
        return posts

    def format_for_analysis(self, posts: List[PpomppuPost]) -> str:
        """분석용 텍스트 포맷"""
        if not posts:
            return "[뽐뿌] 새로운 게시글 없음\n"

        output = ["\n## 뽐뿌 (Ppomppu)\n"]
        for i, post in enumerate(posts[:15], 1):
            cat_str = f"[{post.category}] " if post.category else ""
            output.append(
                f"{i}. {cat_str}{post.title}\n"
                f"   조회: {post.hit} | 추천: {post.recommend} | 댓글: {post.comment_count}\n"
                f"   URL: {post.url}\n"
            )
        return "\n".join(output)
