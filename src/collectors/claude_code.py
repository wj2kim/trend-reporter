"""Claude Code 공식 신호 수집기"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


NPM_PACKAGE_URL = "https://registry.npmjs.org/@anthropic-ai/claude-code"
GITHUB_API_BASE = "https://api.github.com/repos/anthropics/claude-code"


@dataclass
class ClaudeCodePackageInfo:
    """npm 배포 정보"""
    latest: str
    stable: str
    next_version: str
    latest_published_at: str


@dataclass
class ClaudeCodeRelease:
    """GitHub release 정보"""
    tag_name: str
    published_at: str
    body: str
    url: str


@dataclass
class ClaudeCodeIssue:
    """GitHub issue 정보"""
    number: int
    title: str
    created_at: str
    labels: List[str]
    url: str
    bucket: str


class ClaudeCodeCollector:
    """Claude Code 공식 릴리스, npm, 이슈 수집"""

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

    def collect_package_info(self) -> Optional[ClaudeCodePackageInfo]:
        """npm 배포 메타데이터 수집"""
        try:
            resp = self.session.get(NPM_PACKAGE_URL, timeout=20)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"[Claude Code] npm 정보 수집 실패: {e}")
            return None

        dist_tags = payload.get("dist-tags", {})
        latest = dist_tags.get("latest", "")
        stable = dist_tags.get("stable", "")
        next_version = dist_tags.get("next", "")
        latest_published_at = payload.get("time", {}).get(latest, "")

        cache_id = f"claude_code_npm_{latest}_{stable}_{next_version}"
        if self.cache and self.cache.is_seen(cache_id):
            return None

        if self.cache:
            self.cache.mark_seen(cache_id)

        return ClaudeCodePackageInfo(
            latest=latest,
            stable=stable,
            next_version=next_version,
            latest_published_at=latest_published_at,
        )

    def collect_releases(self, limit: int = 3) -> List[ClaudeCodeRelease]:
        """최근 GitHub release 수집"""
        try:
            resp = self.session.get(
                f"{GITHUB_API_BASE}/releases",
                params={"per_page": limit * 2},
                timeout=20,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"[Claude Code] release 수집 실패: {e}")
            return []

        releases = []
        for item in payload:
            tag_name = item.get("tag_name", "")
            if not tag_name:
                continue

            cache_id = f"claude_code_release_{tag_name}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            body = " ".join((item.get("body") or "").split())[:1200]
            releases.append(ClaudeCodeRelease(
                tag_name=tag_name,
                published_at=item.get("published_at", ""),
                body=body,
                url=item.get("html_url", ""),
            ))

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(releases) >= limit:
                break

        return releases

    def collect_issues(self, buckets: List[dict], limit_per_bucket: int = 3) -> Dict[str, List[ClaudeCodeIssue]]:
        """버킷별 open issue 수집"""
        results: Dict[str, List[ClaudeCodeIssue]] = {}

        for bucket in buckets:
            name = bucket.get("name", "issues")
            label = bucket.get("label", "")
            params = {
                "state": "open",
                "per_page": limit_per_bucket * 2,
            }
            if label:
                params["labels"] = label

            try:
                resp = self.session.get(f"{GITHUB_API_BASE}/issues", params=params, timeout=20)
                resp.raise_for_status()
                payload = resp.json()
            except Exception as e:
                print(f"[Claude Code] issue 수집 실패 ({name}): {e}")
                results[name] = []
                continue

            issues = []
            for item in payload:
                if "pull_request" in item:
                    continue

                number = item.get("number")
                if not number:
                    continue

                cache_id = f"claude_code_issue_{number}"
                if self.cache and self.cache.is_seen(cache_id):
                    continue

                issues.append(ClaudeCodeIssue(
                    number=number,
                    title=item.get("title", ""),
                    created_at=item.get("created_at", ""),
                    labels=[label_obj.get("name", "") for label_obj in item.get("labels", [])[:4]],
                    url=item.get("html_url", ""),
                    bucket=name,
                ))

                if self.cache:
                    self.cache.mark_seen(cache_id)

                if len(issues) >= limit_per_bucket:
                    break

            results[name] = issues
            print(f"[Claude Code] {name}: {len(issues)}개 이슈 수집")

        return results

    def collect_all(self, release_limit: int = 3, issue_buckets: Optional[List[dict]] = None, issue_limit: int = 3) -> dict:
        """Claude Code 관련 공식 신호 수집"""
        if issue_buckets is None:
            issue_buckets = []

        package_info = self.collect_package_info()
        releases = self.collect_releases(limit=release_limit)
        issues = self.collect_issues(issue_buckets, limit_per_bucket=issue_limit)

        print(f"[Claude Code] release {len(releases)}개, issue {sum(len(v) for v in issues.values())}개 수집")
        return {
            "package": package_info,
            "releases": releases,
            "issues": issues,
        }

    def format_for_analysis(self, data: dict) -> str:
        """분석용 텍스트 포맷"""
        output = ["\n## Claude Code Official Signals\n"]
        total = 0

        package_info = data.get("package")
        if package_info:
            output.append(
                f"### npm Package\n"
                f"- latest: {package_info.latest}\n"
                f"- stable: {package_info.stable}\n"
                f"- next: {package_info.next_version}\n"
                f"- latest published: {package_info.latest_published_at}\n"
            )
            total += 1

        releases = data.get("releases", [])
        if releases:
            output.append("\n### Recent Releases\n")
            for release in releases:
                output.append(
                    f"- {release.tag_name} ({release.published_at})\n"
                    f"  {release.body[:260]}\n"
                    f"  URL: {release.url}\n"
                )
                total += 1

        issues = data.get("issues", {})
        for bucket, bucket_issues in issues.items():
            if not bucket_issues:
                continue
            output.append(f"\n### Open Issues - {bucket}\n")
            for issue in bucket_issues:
                labels = ", ".join(issue.labels) if issue.labels else "N/A"
                output.append(
                    f"- #{issue.number} {issue.title}\n"
                    f"  Labels: {labels} | Created: {issue.created_at}\n"
                    f"  URL: {issue.url}\n"
                )
                total += 1

        if total == 0:
            return "[Claude Code] 새로운 공식 신호 없음\n"

        return "\n".join(output)
