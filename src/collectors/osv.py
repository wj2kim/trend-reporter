"""OSV 취약점 수집기"""

from dataclasses import dataclass
from typing import List, Optional

import requests

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


OSV_API_URL = "https://api.osv.dev/v1/querybatch"


@dataclass
class OSVVulnerability:
    """OSV 취약점 데이터"""
    package: str
    ecosystem: str
    vuln_id: str
    modified: str
    aliases: List[str]


class OSVCollector:
    """OSV 배치 API를 사용한 패키지 취약점 수집"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache

    def collect_all(self, packages: List[dict], max_vulns_per_package: int = 3) -> dict:
        """패키지 목록에 대한 취약점 조회"""
        if not packages:
            return {}

        payload = {
            "queries": [
                {
                    "package": {
                        "name": pkg["name"],
                        "ecosystem": pkg["ecosystem"],
                    }
                }
                for pkg in packages
            ]
        }

        try:
            resp = self.session.post(OSV_API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            response = resp.json()
        except Exception as e:
            print(f"[OSV] 수집 실패: {e}")
            return {}

        results = {}
        total = 0
        for pkg_cfg, result in zip(packages, response.get("results", [])):
            name = pkg_cfg["name"]
            ecosystem = pkg_cfg["ecosystem"]
            vulns = []
            for vuln in result.get("vulns", []):
                cache_id = f"osv_{ecosystem}_{name}_{vuln.get('id', '')}"
                if self.cache and self.cache.is_seen(cache_id):
                    continue

                vulns.append(OSVVulnerability(
                    package=name,
                    ecosystem=ecosystem,
                    vuln_id=vuln.get("id", ""),
                    modified=vuln.get("modified", ""),
                    aliases=vuln.get("aliases", [])[:3],
                ))

                if self.cache:
                    self.cache.mark_seen(cache_id)

                if len(vulns) >= max_vulns_per_package:
                    break

            results[name] = vulns
            total += len(vulns)
            print(f"[OSV] {name}: {len(vulns)}개 취약점 수집")

        print(f"[OSV] 총 {total}개 취약점 수집")
        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석용 텍스트 포맷"""
        output = []
        total = 0

        for package, vulns in data.items():
            if not vulns:
                continue

            output.append(f"\n## OSV - {package}\n")
            for i, vuln in enumerate(vulns, 1):
                aliases = ", ".join(vuln.aliases) if vuln.aliases else "N/A"
                output.append(
                    f"{i}. {vuln.vuln_id}\n"
                    f"   Ecosystem: {vuln.ecosystem} | Modified: {vuln.modified}\n"
                    f"   Aliases: {aliases}\n"
                )
                total += 1

        if total == 0:
            return "[OSV] 새로운 취약점 없음\n"

        return "\n".join(output)
