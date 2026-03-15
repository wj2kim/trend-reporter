#!/usr/bin/env python3
"""트렌드 리포터 메인 실행 파일"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import json
import yaml
from dotenv import load_dotenv

from cache import ContentCache
from storage import TrendStorage
from collectors import (
    HackerNewsCollector, RSSCollector, DevToCollector, LobstersCollector,
    GitHubTrendingCollector, HuggingFaceCollector, GitHubAPICollector,
    ArxivCollector, OSVCollector, GDELTCollector, FREDCollector,
    SECFilingsCollector, TreasuryPressCollector, ClaudeCodeCollector,
    GeekNewsNewCollector
)
from analyzer import TrendAnalyzer
from publisher import GitHubPagesPublisher


def load_config():
    """설정 파일 로드"""
    config_path = project_root / "config" / "sources.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_previous_reports(limit: int = 10) -> dict:
    """이전 리포트 제목 로드 (중복 방지용)"""
    reports_json = project_root / "docs" / "reports.json"
    previous = {"market": [], "dev": []}

    if not reports_json.exists():
        return previous

    try:
        with open(reports_json, 'r', encoding='utf-8') as f:
            reports = json.load(f)

        for r in reports[:limit * 2]:  # 각 카테고리별로 limit개씩
            category = r.get("category", "")
            title = r.get("title", "").split(" | ")[0]  # 날짜 부분 제거
            if category == "market" and len(previous["market"]) < limit:
                previous["market"].append(title)
            elif category == "dev" and len(previous["dev"]) < limit:
                previous["dev"].append(title)

        print(f"[중복방지] 이전 리포트 로드: Market {len(previous['market'])}개, Dev {len(previous['dev'])}개")
    except Exception as e:
        print(f"[중복방지] 이전 리포트 로드 실패: {e}")

    return previous


def run_collection_step(step_no: int, total_steps: int, label: str, collect_fn, data_buckets: dict, storage: TrendStorage = None):
    """수집 단계를 실행하고 결과를 누적"""
    print(f"\n[{step_no}/{total_steps}] {label} 데이터 수집 중...")
    try:
        result = collect_fn()
        if isinstance(result, dict):
            for bucket, text in result.items():
                if text:
                    data_buckets[bucket].append(text)
                    if storage:
                        storage.save(source=label, category=bucket, content=text)
        elif result:
            data_buckets["dev"].append(result)
            if storage:
                storage.save(source=label, category="dev", content=result)
    except Exception as e:
        print(f"[{label}] 수집 실패: {e}")


def collect_and_format(collector, collect_method: str, format_method: str, **kwargs) -> str:
    """collector의 수집 및 포맷 메서드를 순서대로 실행"""
    data = getattr(collector, collect_method)(**kwargs)
    return getattr(collector, format_method)(data)


def add_to_bucket(bucket: str, text: str) -> dict:
    """단일 버퍼에 결과를 적재"""
    return {bucket: text}


def add_to_buckets(**kwargs) -> dict:
    """여러 버퍼에 결과를 적재"""
    return {bucket: text for bucket, text in kwargs.items() if text}


def main():
    """메인 실행 함수"""
    # 환경변수 로드
    load_dotenv(project_root / ".env")

    print("=" * 50)
    print("트렌드 리포터 시작")
    print("=" * 50)

    # 설정 로드
    config = load_config()

    # 캐시 및 저장소 초기화
    cache = ContentCache(cache_dir=str(project_root / "cache"))
    storage = TrendStorage()

    # 수집 데이터를 market/dev 버퍼로 분리
    data_buckets = {
        "market": [],
        "dev": [],
    }
    total_steps = 15  # run_collection_step 호출 수와 일치시킬 것
    hn_collector = HackerNewsCollector(cache=cache)
    devto_collector = DevToCollector(cache=cache)
    lobsters_collector = LobstersCollector(cache=cache)
    rss_collector = RSSCollector(cache=cache)
    github_trending_collector = GitHubTrendingCollector(cache=cache)
    github_api_collector = GitHubAPICollector(cache=cache)
    arxiv_collector = ArxivCollector(cache=cache)
    osv_collector = OSVCollector(cache=cache)
    gdelt_collector = GDELTCollector(cache=cache)
    fred_collector = FREDCollector(cache=cache)
    sec_collector = SECFilingsCollector(cache=cache)
    treasury_collector = TreasuryPressCollector(cache=cache)
    claude_code_collector = ClaudeCodeCollector(cache=cache)
    geeknews_collector = GeekNewsNewCollector(cache=cache)
    hf_collector = HuggingFaceCollector(cache=cache)

    run_collection_step(
        1, total_steps, "Hacker News",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                hn_collector,
                "collect_all",
                "format_for_analysis",
                top_limit=config["hackernews"].get("top_stories", 20),
                best_limit=config["hackernews"].get("best_stories", 10),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        2, total_steps, "DEV.to",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                devto_collector,
                "collect_all",
                "format_for_analysis",
                general_limit=config.get("devto", {}).get("limit", 20),
                tags=config.get("devto", {}).get("tags"),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        3, total_steps, "Lobste.rs",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                lobsters_collector,
                "collect_all",
                "format_for_analysis",
                hottest_limit=config.get("lobsters", {}).get("hottest", 20),
                newest_limit=config.get("lobsters", {}).get("newest", 10),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        4, total_steps, "RSS",
        lambda: (
            lambda rss_data: add_to_buckets(
                market=rss_collector.format_for_analysis(
                    rss_data,
                    categories=["world", "stocks", "macro", "community"],
                ),
                dev=rss_collector.format_for_analysis(
                    rss_data,
                    categories=["tech", "ai", "trending"],
                ),
            )
        )(
            rss_collector.collect_all(
                feeds_config=config["rss"].get("feeds", []),
                items_per_feed=config["rss"].get("items_per_feed", 8),
            )
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        5, total_steps, "GitHub Trending",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                github_trending_collector,
                "collect_all",
                "format_for_analysis",
                limit=10,
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        6, total_steps, "GitHub API",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                github_api_collector,
                "collect_all",
                "format_for_analysis",
                queries=config.get("github_api", {}).get("queries", []),
                days_back=config.get("github_api", {}).get("days_back", 7),
                per_query=config.get("github_api", {}).get("per_query", 5),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        7, total_steps, "Claude Code",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                claude_code_collector,
                "collect_all",
                "format_for_analysis",
                release_limit=config.get("claude_code", {}).get("release_limit", 3),
                issue_buckets=config.get("claude_code", {}).get("issue_buckets", []),
                issue_limit=config.get("claude_code", {}).get("issue_limit", 3),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        8, total_steps, "GeekNews",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                geeknews_collector,
                "collect_all",
                "format_for_analysis",
                limit=config.get("geeknews_new", {}).get("limit", 12),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        9, total_steps, "arXiv",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                arxiv_collector,
                "collect_all",
                "format_for_analysis",
                queries=config.get("arxiv", {}).get("queries", []),
                per_query=config.get("arxiv", {}).get("per_query", 5),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        10, total_steps, "OSV",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                osv_collector,
                "collect_all",
                "format_for_analysis",
                packages=config.get("osv", {}).get("packages", []),
                max_vulns_per_package=config.get("osv", {}).get("max_vulns_per_package", 3),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        11, total_steps, "GDELT",
        lambda: add_to_bucket(
            "market",
            collect_and_format(
                gdelt_collector,
                "collect_all",
                "format_for_analysis",
                queries=config.get("gdelt", {}).get("queries", []),
                max_records=config.get("gdelt", {}).get("max_records", 8),
                timespan=config.get("gdelt", {}).get("timespan", "24h"),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        12, total_steps, "FRED",
        lambda: add_to_bucket(
            "market",
            collect_and_format(
                fred_collector,
                "collect_all",
                "format_for_analysis",
                series=config.get("fred", {}).get("series", []),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        13, total_steps, "SEC",
        lambda: add_to_bucket(
            "market",
            collect_and_format(
                sec_collector,
                "collect_all",
                "format_for_analysis",
                companies=config.get("sec", {}).get("companies", []),
                limit_per_company=config.get("sec", {}).get("limit_per_company", 3),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        14, total_steps, "Treasury",
        lambda: add_to_bucket(
            "market",
            collect_and_format(
                treasury_collector,
                "collect_all",
                "format_for_analysis",
                limit=config.get("treasury", {}).get("limit", 6),
            ),
        ),
        data_buckets,
        storage,
    )

    run_collection_step(
        15, total_steps, "Hugging Face",
        lambda: add_to_bucket(
            "dev",
            collect_and_format(
                hf_collector,
                "collect_all",
                "format_for_analysis",
                trending_limit=8,
                recent_limit=5,
            ),
        ),
        data_buckets,
        storage,
    )

    # 캐시 및 저장소 저장
    cache.save()
    storage.close()

    market_data = "\n".join(data_buckets["market"]).strip()
    dev_data = "\n".join(data_buckets["dev"]).strip()

    # 수집 데이터가 거의 없으면 분석 없이 종료
    if len(market_data) < 300 and len(dev_data) < 300:
        print("\n새로운 데이터가 거의 없습니다. 분석을 건너뜁니다.")
        return 0

    if len(market_data) < 300:
        market_data = "[시장/정세 관련 새 데이터가 거의 없습니다. 리포트가 필요하면 '새로운 업데이트 없음'을 중심으로 정리하세요.]\n"

    if len(dev_data) < 300:
        dev_data = "[개발/AI 관련 새 데이터가 거의 없습니다. 리포트가 필요하면 '새로운 업데이트 없음'을 중심으로 정리하세요.]\n"

    # 이전 리포트 로드 (중복 방지)
    previous_reports = load_previous_reports(limit=5)

    # Gemini로 분석 (두 개의 리포트 생성)
    print("\n[분석] Gemini API로 분석 중...")
    analyzer = TrendAnalyzer()
    date_str = analyzer.create_report_header()

    # 1. 세계 정세 & 주식 리포트
    print("  - 세계 정세 & 주식 리포트 생성 중...")
    world_headline, world_keywords, world_insight, world_report = analyzer.analyze_world_market(
        market_data,
        previous_titles=previous_reports["market"]
    )
    world_title = f"{world_headline} | {date_str}"

    # 2. 개발 & AI 리포트
    print("  - 개발 & AI 리포트 생성 중...")
    dev_headline, dev_keywords, dev_insight, dev_report = analyzer.analyze_dev_ai(
        dev_data,
        previous_titles=previous_reports["dev"]
    )
    dev_title = f"{dev_headline} | {date_str}"

    print("\n" + "=" * 50)
    print("[세계정세] " + world_title)
    print("=" * 50)
    print(world_report[:500] + "..." if len(world_report) > 500 else world_report)

    print("\n" + "=" * 50)
    print("[개발/AI] " + dev_title)
    print("=" * 50)
    print(dev_report[:500] + "..." if len(dev_report) > 500 else dev_report)

    # GitHub Pages로 저장 (오전 실행 또는 수동 실행일 때만)
    publish_pages = os.getenv("PUBLISH_PAGES", "true").lower() == "true"
    publish_success = True

    if publish_pages:
        print("\n[저장] GitHub Pages용 HTML 생성 중...")
        publisher = GitHubPagesPublisher()

        world_success = publisher.publish(world_title, world_report, category="market", keywords=world_keywords, insight=world_insight)
        dev_success = publisher.publish(dev_title, dev_report, category="dev", keywords=dev_keywords, insight=dev_insight)
        publish_success = world_success and dev_success

        if publish_success:
            print("✅ GitHub Pages 저장 완료!")
        else:
            print("❌ GitHub Pages 저장 실패")
    else:
        print("\n[저장] GitHub Pages 저장 건너뜀 (오전 실행에서만 저장)")

    return 0 if publish_success else 1


if __name__ == "__main__":
    sys.exit(main())
