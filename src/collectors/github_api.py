"""GitHub 공식 API 기반 최근 저장소 수집기"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


GITHUB_API_BASE = "https://api.github.com"


@dataclass
class GitHubRepo:
    """GitHub 검색 결과 저장소"""
    full_name: str
    description: str
    language: str
    stars: int
    updated_at: str
    url: str
    query_name: str


class GitHubAPICollector:
    """GitHub Search API를 사용한 최근 활발한 저장소 수집"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "TrendReporter/1.0",
        }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.session.headers.update(headers)
        self.cache = cache

    def collect_query(self, query_cfg: dict, days_back: int = 7, per_query: int = 5) -> List[GitHubRepo]:
        """단일 GitHub 검색 쿼리 실행"""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        base_query = query_cfg.get("query", "").strip()
        if not base_query:
            return []

        params = {
            "q": f"{base_query} pushed:>={cutoff}",
            "sort": "stars",
            "order": "desc",
            "per_page": per_query * 2,
        }

        try:
            resp = self.session.get(f"{GITHUB_API_BASE}/search/repositories", params=params, timeout=20)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"[GitHub API] {query_cfg.get('name', 'query')} 수집 실패: {e}")
            return []

        repos = []
        for item in payload.get("items", []):
            full_name = item.get("full_name", "")
            if not full_name:
                continue

            cache_id = f"gh_api_{full_name}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            repos.append(GitHubRepo(
                full_name=full_name,
                description=item.get("description", "") or "",
                language=item.get("language", "") or "",
                stars=item.get("stargazers_count", 0),
                updated_at=item.get("updated_at", ""),
                url=item.get("html_url", ""),
                query_name=query_cfg.get("name", "general"),
            ))

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(repos) >= per_query:
                break

        return repos

    def collect_all(self, queries: List[dict], days_back: int = 7, per_query: int = 5) -> dict:
        """쿼리별 저장소 검색"""
        results = {}
        total = 0
        for query_cfg in queries:
            name = query_cfg.get("name", "general")
            repos = self.collect_query(query_cfg, days_back=days_back, per_query=per_query)
            results[name] = repos
            total += len(repos)
            print(f"[GitHub API] {name}: {len(repos)}개 저장소 수집")

        print(f"[GitHub API] 총 {total}개 저장소 수집")
        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석용 텍스트 포맷"""
        output = []
        total = 0

        for name, repos in data.items():
            if not repos:
                continue

            output.append(f"\n## GitHub Search API - {name.upper()}\n")
            for i, repo in enumerate(repos[:5], 1):
                output.append(
                    f"{i}. {repo.full_name}\n"
                    f"   Stars: {repo.stars:,} | Language: {repo.language or 'N/A'} | Updated: {repo.updated_at}\n"
                    f"   {repo.description[:200]}\n"
                    f"   URL: {repo.url}\n"
                )
                total += 1

        if total == 0:
            return "[GitHub API] 새로운 저장소 없음\n"

        return "\n".join(output)
