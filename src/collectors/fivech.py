"""5ch (5ちゃんねる) 데이터 수집기"""

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
class FiveChThread:
    """5ch 스레드 데이터"""
    id: str
    title: str
    url: str
    res_count: int
    board: str


class FiveChCollector:
    """5ch 인기 스레드 수집"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.cache = cache

    def collect_posts(self, limit: int = 20) -> List[FiveChThread]:
        """5ch 뉴스속보+ 인기 스레드 수집"""
        posts = []

        try:
            # 뉴스속보+ (newsplus) - 가장 활발한 게시판
            resp = self.session.get(
                "https://headline.5ch.net/bbynews/",
                timeout=15
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('li'):
                try:
                    link = item.select_one('a')
                    if not link:
                        continue

                    href = link.get('href', '')
                    if not href or '5ch.net' not in href:
                        continue

                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue

                    # 스레드 ID 추출
                    match = re.search(r'/(\d+)/?$', href)
                    if not match:
                        continue
                    thread_id = match.group(1)

                    cache_id = f"5ch_{thread_id}"
                    if self.cache and self.cache.is_seen(cache_id):
                        continue

                    # 레스 수 추출 (타이틀에서)
                    res_match = re.search(r'\((\d+)\)$', title)
                    res_count = int(res_match.group(1)) if res_match else 0

                    # 레스 수 부분 제거
                    clean_title = re.sub(r'\s*\(\d+\)$', '', title)

                    # 게시판 이름 추출
                    board_match = re.search(r'://([^.]+)\.5ch\.net', href)
                    board = board_match.group(1) if board_match else "5ch"

                    posts.append(FiveChThread(
                        id=thread_id,
                        title=clean_title,
                        url=href,
                        res_count=res_count,
                        board=board
                    ))

                    if self.cache:
                        self.cache.mark_seen(cache_id)

                    if len(posts) >= limit:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            print(f"[5ch] 수집 실패: {e}")

        print(f"[5ch] {len(posts)}개 스레드 수집")
        return posts

    def format_for_analysis(self, posts: List[FiveChThread]) -> str:
        """분석용 텍스트 포맷"""
        if not posts:
            return "[5ch] 새로운 스레드 없음\n"

        output = ["\n## 5ch (5ちゃんねる)\n"]
        for i, post in enumerate(posts[:15], 1):
            output.append(
                f"{i}. {post.title}\n"
                f"   레스: {post.res_count} | 게시판: {post.board}\n"
                f"   URL: {post.url}\n"
            )
        return "\n".join(output)
