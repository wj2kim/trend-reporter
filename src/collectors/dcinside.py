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

    # 주식 관련 갤러리
    STOCK_GALLERIES = [
        ("stockus", "미국주식"),
        ("stock", "국내주식"),
        ("bitcoin", "비트코인"),
    ]

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        self.cache = cache

    def _parse_gallery(self, gallery_id: str, gallery_name: str, limit: int = 10) -> List[DCPost]:
        """특정 갤러리 파싱"""
        posts = []
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/board/lists?id={gallery_id}",
                timeout=15
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.ub-content'):
                try:
                    if 'us-post' in item.get('class', []):
                        continue

                    title_elem = item.select_one('.gall_tit a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get('href', '')

                    post_id = item.get('data-no', '')
                    if not post_id:
                        continue

                    cache_id = f"dc_{gallery_id}_{post_id}"
                    if self.cache and self.cache.is_seen(cache_id):
                        continue

                    hit_elem = item.select_one('.gall_count')
                    hit = 0
                    if hit_elem:
                        hit_text = hit_elem.get_text(strip=True)
                        hit = int(hit_text) if hit_text.isdigit() else 0

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
                        gallery=gallery_name
                    ))

                    if self.cache:
                        self.cache.mark_seen(cache_id)

                    if len(posts) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"[DCInside] {gallery_name} 수집 실패: {e}")

        return posts

    def collect_posts(self, limit: int = 20) -> List[DCPost]:
        """힛갤 인기글 수집"""
        return self._parse_gallery("hit", "힛갤", limit)

    def collect_stock_posts(self, limit_per_gallery: int = 10) -> List[DCPost]:
        """주식 관련 갤러리 수집"""
        all_posts = []
        for gall_id, gall_name in self.STOCK_GALLERIES:
            posts = self._parse_gallery(gall_id, gall_name, limit_per_gallery)
            all_posts.extend(posts)
            print(f"[DCInside] {gall_name} {len(posts)}개 수집")
        return all_posts

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

    def format_stock_for_analysis(self, posts: List[DCPost]) -> str:
        """주식 게시글 분석용 텍스트 포맷"""
        if not posts:
            return "[디시인사이드 주식] 새로운 게시글 없음\n"

        output = ["\n## 디시인사이드 주식갤러리\n"]
        for i, post in enumerate(posts[:20], 1):
            output.append(
                f"{i}. [{post.gallery}] {post.title}\n"
                f"   조회: {post.hit} | 추천: {post.recommend}\n"
                f"   URL: {post.url}\n"
            )
        return "\n".join(output)
