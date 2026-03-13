"""arXiv Atom API 수집기"""

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional

import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass
class ArxivPaper:
    """arXiv 논문 데이터"""
    title: str
    url: str
    updated: str
    summary: str
    authors: List[str]
    query_name: str


class ArxivCollector:
    """arXiv API를 사용한 최신 AI/개발 논문 수집"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrendReporter/1.0"
        })
        self.cache = cache

    def collect_query(self, query_cfg: dict, per_query: int = 5) -> List[ArxivPaper]:
        """단일 검색 쿼리 실행"""
        params = {
            "search_query": query_cfg.get("search_query", ""),
            "start": 0,
            "max_results": per_query * 2,
            "sortBy": "lastUpdatedDate",
            "sortOrder": "descending",
        }
        if not params["search_query"]:
            return []

        try:
            resp = self.session.get(ARXIV_API_URL, params=params, timeout=30)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
        except Exception as e:
            print(f"[arXiv] {query_cfg.get('name', 'query')} 수집 실패: {e}")
            return []

        papers = []
        for entry in root.findall("atom:entry", ATOM_NS):
            url = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
            title = " ".join((entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").split())
            updated = entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
            summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").split())
            authors = [
                (author.findtext("atom:name", default="", namespaces=ATOM_NS) or "").strip()
                for author in entry.findall("atom:author", ATOM_NS)
            ]

            if not url or not title:
                continue

            cache_id = f"arxiv_{url}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            papers.append(ArxivPaper(
                title=title,
                url=url,
                updated=updated,
                summary=summary[:400],
                authors=[a for a in authors if a][:4],
                query_name=query_cfg.get("name", "general"),
            ))

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(papers) >= per_query:
                break

        return papers

    def collect_all(self, queries: List[dict], per_query: int = 5) -> dict:
        """여러 arXiv 쿼리 실행"""
        results = {}
        total = 0

        for query_cfg in queries:
            name = query_cfg.get("name", "general")
            papers = self.collect_query(query_cfg, per_query=per_query)
            results[name] = papers
            total += len(papers)
            print(f"[arXiv] {name}: {len(papers)}개 논문 수집")

        print(f"[arXiv] 총 {total}개 논문 수집")
        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석용 텍스트 포맷"""
        output = []
        total = 0

        for name, papers in data.items():
            if not papers:
                continue

            output.append(f"\n## arXiv - {name.upper()}\n")
            for i, paper in enumerate(papers[:5], 1):
                authors = ", ".join(paper.authors[:3]) if paper.authors else "unknown"
                output.append(
                    f"{i}. {paper.title}\n"
                    f"   Authors: {authors}\n"
                    f"   Updated: {paper.updated}\n"
                    f"   Summary: {paper.summary[:220]}\n"
                    f"   URL: {paper.url}\n"
                )
                total += 1

        if total == 0:
            return "[arXiv] 새로운 논문 없음\n"

        return "\n".join(output)
