# from .reddit import RedditCollector  # Reddit API 승인 후 활성화
from .hackernews import HackerNewsCollector
from .rss import RSSCollector
from .devto import DevToCollector
from .lobsters import LobstersCollector
from .github_trending import GitHubTrendingCollector
from .huggingface import HuggingFaceCollector

# 커뮤니티 수집기
from .clien import ClienCollector
from .dcinside import DCInsideCollector
from .fmkorea import FMKoreaCollector
from .ppomppu import PpomppuCollector
from .ruliweb import RuliwebCollector
from .fivech import FiveChCollector

__all__ = [
    'HackerNewsCollector',
    'RSSCollector',
    'DevToCollector',
    'LobstersCollector',
    'GitHubTrendingCollector',
    'HuggingFaceCollector',
    # 커뮤니티
    'ClienCollector',
    'DCInsideCollector',
    'FMKoreaCollector',
    'PpomppuCollector',
    'RuliwebCollector',
    'FiveChCollector',
]
