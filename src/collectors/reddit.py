"""Reddit 데이터 수집기"""

import os
import praw
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


@dataclass
class RedditPost:
    """Reddit 게시물 데이터"""
    id: str
    title: str
    url: str
    score: int
    num_comments: int
    subreddit: str
    created_utc: datetime
    selftext: str = ""


class RedditCollector:
    """Reddit API를 사용하여 게시물을 수집하는 클래스"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "TrendReporter/1.0"),
        )
        self.cache = cache

    def collect_subreddit(
        self,
        subreddit_name: str,
        limit: int = 15,
        sort_by: str = "hot"
    ) -> List[RedditPost]:
        """단일 subreddit에서 게시물 수집"""
        posts = []
        subreddit = self.reddit.subreddit(subreddit_name)

        if sort_by == "hot":
            submissions = subreddit.hot(limit=limit * 2)  # 캐시된 것 고려해 더 가져옴
        elif sort_by == "top":
            submissions = subreddit.top(limit=limit * 2, time_filter="day")
        else:
            submissions = subreddit.new(limit=limit * 2)

        for submission in submissions:
            # 고정 게시물 제외
            if submission.stickied:
                continue

            # 캐시된 게시물 스킵
            post_id = f"reddit_{submission.id}"
            if self.cache and self.cache.is_seen(post_id):
                continue

            posts.append(RedditPost(
                id=submission.id,
                title=submission.title,
                url=submission.url,
                score=submission.score,
                num_comments=submission.num_comments,
                subreddit=subreddit_name,
                created_utc=datetime.fromtimestamp(submission.created_utc),
                selftext=submission.selftext[:500] if submission.selftext else ""
            ))

            # 캐시에 추가
            if self.cache:
                self.cache.mark_seen(post_id)

            # 충분히 모았으면 중단
            if len(posts) >= limit:
                break

        return posts

    def collect_by_category(
        self,
        categories: Dict[str, List[str]],
        posts_per_subreddit: int = 15,
        sort_by: str = "hot"
    ) -> Dict[str, List[RedditPost]]:
        """카테고리별로 게시물 수집"""
        results = {}

        for category, subreddits in categories.items():
            category_posts = []
            for subreddit in subreddits:
                try:
                    posts = self.collect_subreddit(
                        subreddit,
                        limit=posts_per_subreddit,
                        sort_by=sort_by
                    )
                    category_posts.extend(posts)
                    print(f"[Reddit] r/{subreddit}: {len(posts)}개 새 게시물")
                except Exception as e:
                    print(f"[Reddit] r/{subreddit} 수집 실패: {e}")

            # 점수 기준 정렬
            category_posts.sort(key=lambda x: x.score, reverse=True)
            results[category] = category_posts

        return results

    def format_for_analysis(self, data: Dict[str, List[RedditPost]]) -> str:
        """분석을 위한 텍스트 포맷"""
        output = []
        total_posts = 0

        for category, posts in data.items():
            if not posts:
                continue
            output.append(f"\n## Reddit - {category.upper()}\n")
            for i, post in enumerate(posts[:20], 1):  # 카테고리당 상위 20개
                output.append(
                    f"{i}. [{post.subreddit}] {post.title}\n"
                    f"   Score: {post.score} | Comments: {post.num_comments}\n"
                    f"   URL: {post.url}\n"
                )
                if post.selftext:
                    output.append(f"   내용: {post.selftext[:200]}...\n")
                total_posts += 1

        if total_posts == 0:
            return "[Reddit] 새로운 게시물 없음\n"

        return "\n".join(output)
