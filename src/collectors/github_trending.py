"""GitHub Trending 데이터 수집기"""

import os
import re
import requests
from typing import List, Optional
from dataclasses import dataclass

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


@dataclass
class TrendingRepo:
    """GitHub Trending 레포지토리 데이터"""
    name: str
    description: str
    language: str
    stars: int
    stars_today: int
    forks: int
    url: str


class GitHubTrendingCollector:
    """GitHub Trending 페이지에서 인기 레포를 수집하는 클래스"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.cache = cache

    def _parse_number(self, text: str) -> int:
        """숫자 파싱 (1,234 -> 1234, 1.2k -> 1200)"""
        if not text:
            return 0
        text = text.strip().replace(',', '')
        if 'k' in text.lower():
            return int(float(text.lower().replace('k', '')) * 1000)
        try:
            return int(text)
        except:
            return 0

    def collect_trending(self, language: str = "", since: str = "daily", limit: int = 15) -> List[TrendingRepo]:
        """GitHub Trending 수집

        Args:
            language: 프로그래밍 언어 (빈 문자열이면 전체)
            since: daily, weekly, monthly
            limit: 가져올 레포 수
        """
        url = f"https://github.com/trending/{language}?since={since}"

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"[GitHub] Trending 페이지 요청 실패: {e}")
            return []

        repos = []

        # 각 레포 article 태그 파싱
        repo_pattern = r'<article class="Box-row">(.*?)</article>'
        repo_matches = re.findall(repo_pattern, html, re.DOTALL)

        for repo_html in repo_matches[:limit]:
            try:
                # 레포 이름
                name_match = re.search(r'href="/([^"]+)"[^>]*class="[^"]*Link[^"]*"', repo_html)
                if not name_match:
                    name_match = re.search(r'<h2[^>]*>.*?href="/([^"]+)"', repo_html, re.DOTALL)

                if not name_match:
                    continue

                full_name = name_match.group(1).strip()

                # 캐시된 레포 스킵
                repo_id = f"gh_{full_name}"
                if self.cache and self.cache.is_seen(repo_id):
                    continue

                # 설명
                desc_match = re.search(r'<p class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', repo_html, re.DOTALL)
                description = ""
                if desc_match:
                    description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

                # 언어
                lang_match = re.search(r'itemprop="programmingLanguage">(.*?)<', repo_html)
                language = lang_match.group(1).strip() if lang_match else ""

                # 전체 스타
                stars_match = re.search(r'href="/[^/]+/[^/]+/stargazers"[^>]*>\s*<[^>]+>\s*</[^>]+>\s*([\d,]+)', repo_html)
                if not stars_match:
                    stars_match = re.search(r'stargazers[^>]*>.*?([\d,]+)', repo_html, re.DOTALL)
                stars = self._parse_number(stars_match.group(1)) if stars_match else 0

                # 오늘 스타
                today_match = re.search(r'([\d,]+)\s*stars?\s*today', repo_html, re.IGNORECASE)
                if not today_match:
                    today_match = re.search(r'([\d,]+)\s*stars?\s*this\s*week', repo_html, re.IGNORECASE)
                stars_today = self._parse_number(today_match.group(1)) if today_match else 0

                # 포크
                forks_match = re.search(r'href="/[^/]+/[^/]+/forks"[^>]*>\s*<[^>]+>\s*</[^>]+>\s*([\d,]+)', repo_html)
                forks = self._parse_number(forks_match.group(1)) if forks_match else 0

                repos.append(TrendingRepo(
                    name=full_name,
                    description=description[:200] if description else "",
                    language=language,
                    stars=stars,
                    stars_today=stars_today,
                    forks=forks,
                    url=f"https://github.com/{full_name}"
                ))

                # 캐시에 추가
                if self.cache:
                    self.cache.mark_seen(repo_id)

            except Exception as e:
                continue

        return repos

    def collect_all(self, limit: int = 15) -> dict:
        """전체 트렌딩과 주요 언어별 트렌딩 수집"""
        results = {
            "all": self.collect_trending(language="", limit=limit),
            "python": self.collect_trending(language="python", limit=5),
            "typescript": self.collect_trending(language="typescript", limit=5),
        }

        total = sum(len(v) for v in results.values())
        print(f"[GitHub] 총 {total}개 트렌딩 레포 수집")

        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석을 위한 텍스트 포맷"""
        output = ["\n## GitHub Trending\n"]

        all_repos = data.get("all", [])

        if not all_repos:
            return "[GitHub] 새로운 트렌딩 레포 없음\n"

        output.append("### 오늘의 인기 레포\n")
        for i, repo in enumerate(all_repos[:10], 1):
            lang_str = f"[{repo.language}] " if repo.language else ""
            stars_today_str = f" (+{repo.stars_today} today)" if repo.stars_today else ""
            output.append(
                f"{i}. {lang_str}{repo.name}\n"
                f"   {repo.description}\n"
                f"   Stars: {repo.stars:,}{stars_today_str}\n"
                f"   {repo.url}\n"
            )

        # Python 트렌딩
        python_repos = data.get("python", [])
        if python_repos:
            output.append("\n### Python 트렌딩\n")
            for repo in python_repos[:3]:
                output.append(f"- {repo.name}: {repo.description[:100]}\n")

        # TypeScript 트렌딩
        ts_repos = data.get("typescript", [])
        if ts_repos:
            output.append("\n### TypeScript 트렌딩\n")
            for repo in ts_repos[:3]:
                output.append(f"- {repo.name}: {repo.description[:100]}\n")

        return "\n".join(output)
