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

    # 게시판 ID
    BOARDS = {
        "hot": "/hot.php",  # 핫게시판
        "stock": "/zboard/zboard.php?id=stock",  # 주식
        "bitcoin": "/zboard/zboard.php?id=bitcoin",  # 코인
    }

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.cache = cache

    def _parse_board(self, board_url: str, board_name: str, limit: int = 15) -> List[PpomppuPost]:
        """특정 게시판 파싱"""
        posts = []
        try:
            resp = self.session.get(
                f"{self.BASE_URL}{board_url}",
                timeout=15
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('tr.line, tr.list0, tr.list1'):
                try:
                    title_elem = item.select_one('.title a, td.title a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get('href', '')

                    match = re.search(r'no=(\d+)', href)
                    if not match:
                        continue
                    post_id = match.group(1)

                    cache_id = f"ppomppu_{board_name}_{post_id}"
                    if self.cache and self.cache.is_seen(cache_id):
                        continue

                    tds = item.select('td')
                    hit = 0
                    recommend = 0

                    if len(tds) >= 5:
                        hit_text = tds[-1].get_text(strip=True).replace(',', '')
                        hit = int(hit_text) if hit_text.isdigit() else 0
                        rec_text = tds[-2].get_text(strip=True).replace(',', '')
                        recommend = int(rec_text) if rec_text.lstrip('-').isdigit() else 0

                    comment_elem = item.select_one('.list_comment2')
                    comment_count = 0
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
                        category=board_name
                    ))

                    if self.cache:
                        self.cache.mark_seen(cache_id)

                    if len(posts) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"[Ppomppu] {board_name} 수집 실패: {e}")

        return posts

    def collect_posts(self, limit: int = 20) -> List[PpomppuPost]:
        """핫게시판 인기글 수집"""
        posts = self._parse_board(self.BOARDS["hot"], "핫게시판", limit)
        print(f"[Ppomppu] {len(posts)}개 게시글 수집")
        return posts

    def collect_stock_posts(self, limit_per_board: int = 10) -> List[PpomppuPost]:
        """주식/코인 게시판 수집"""
        all_posts = []
        for board_name in ["stock", "bitcoin"]:
            board_label = "주식" if board_name == "stock" else "코인"
            posts = self._parse_board(self.BOARDS[board_name], board_label, limit_per_board)
            all_posts.extend(posts)
            print(f"[Ppomppu] {board_label} {len(posts)}개 수집")
        return all_posts

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

    def format_stock_for_analysis(self, posts: List[PpomppuPost]) -> str:
        """주식 게시글 분석용 텍스트 포맷"""
        if not posts:
            return "[뽐뿌 주식/코인] 새로운 게시글 없음\n"

        output = ["\n## 뽐뿌 주식/코인\n"]
        for i, post in enumerate(posts[:15], 1):
            cat_str = f"[{post.category}] " if post.category else ""
            output.append(
                f"{i}. {cat_str}{post.title}\n"
                f"   조회: {post.hit} | 추천: {post.recommend} | 댓글: {post.comment_count}\n"
                f"   URL: {post.url}\n"
            )
        return "\n".join(output)
