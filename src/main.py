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


def store_collected_data(storage: TrendStorage, collectors: dict):
    """수집기별 구조화된 데이터를 항목 단위로 DB에 저장"""
    try:
        for name, (collector, raw_data, category) in collectors.items():
            if raw_data is None:
                continue
            items = _extract_items(name, raw_data, category)
            if items:
                storage.save_items(items)
                print(f"[Storage] {name}: {len(items)}개 항목 저장")
        storage.flush()
    except Exception as e:
        print(f"[Storage] 저장 실패: {e}")


def _extract_items(source: str, raw_data, category: str) -> list:
    """수집기 데이터를 항목 단위 dict 리스트로 변환"""
    items = []

    if source == "Hacker News":
        for stories in raw_data.values():
            for s in stories:
                items.append({"source": source, "category": category,
                              "title": s.title, "url": s.url, "score": s.score,
                              "meta": f"comments:{s.num_comments} by:{s.author}"})

    elif source == "DEV.to":
        for articles in raw_data.values():
            for a in articles:
                items.append({"source": source, "category": category,
                              "title": a.title, "url": a.url,
                              "score": a.positive_reactions_count,
                              "body": a.description,
                              "meta": f"tags:{','.join(a.tags[:3])} comments:{a.comments_count}"})

    elif source == "Lobsters":
        for stories in raw_data.values():
            for s in stories:
                items.append({"source": source, "category": category,
                              "title": s.title, "url": s.url, "score": s.score,
                              "meta": f"tags:{','.join(s.tags[:3])} comments:{s.comment_count}"})

    elif source.startswith("RSS"):
        market_cats = {"world", "stocks", "macro", "community"}
        dev_cats = {"tech", "ai", "trending"}
        target_cats = market_cats if category == "market" else dev_cats
        for cat_name, cat_items in raw_data.items():
            if cat_name not in target_cats:
                continue
            for r in cat_items:
                items.append({"source": f"RSS/{r.source}", "category": category,
                              "title": r.title, "url": r.url, "body": r.summary})

    elif source == "GitHub Trending":
        for repos in raw_data.values():
            for r in repos:
                items.append({"source": source, "category": category,
                              "title": r.name, "url": r.url, "score": r.stars,
                              "body": r.description,
                              "meta": f"lang:{r.language} today:+{r.stars_today}"})

    elif source == "GitHub API":
        for repos in raw_data.values():
            for r in repos:
                items.append({"source": source, "category": category,
                              "title": r.full_name, "url": r.url, "score": r.stars,
                              "body": r.description,
                              "meta": f"lang:{r.language} query:{r.query_name}"})

    elif source == "arXiv":
        for papers in raw_data.values():
            for p in papers:
                items.append({"source": source, "category": category,
                              "title": p.title, "url": p.url,
                              "body": p.summary[:500],
                              "meta": f"authors:{','.join(p.authors[:3])}"})

    elif source == "GDELT":
        for articles in raw_data.values():
            for a in articles:
                items.append({"source": source, "category": category,
                              "title": a.title, "url": a.url,
                              "meta": f"domain:{a.domain}"})

    elif source == "FRED":
        for obs in (raw_data if isinstance(raw_data, list) else []):
            items.append({"source": source, "category": category,
                          "title": f"{obs.name} ({obs.series_id})",
                          "body": f"{obs.date}: {obs.value} (prev: {obs.previous_value})",
                          "meta": f"category:{obs.category}"})

    elif source == "SEC":
        for filings in raw_data.values():
            for f in filings:
                items.append({"source": source, "category": category,
                              "title": f"{f.company} ({f.ticker}) - {f.form}",
                              "url": f.url,
                              "meta": f"date:{f.filing_date}"})

    elif source == "Treasury":
        for pr in (raw_data if isinstance(raw_data, list) else []):
            items.append({"source": source, "category": category,
                          "title": pr.title, "url": pr.url,
                          "meta": f"date:{pr.date}"})

    elif source == "Claude Code":
        releases = raw_data.get("releases", [])
        for r in releases:
            items.append({"source": source, "category": category,
                          "title": f"Release {r.tag_name}", "url": r.url,
                          "body": r.body[:500] if r.body else ""})
        for bucket_name, issues in raw_data.get("issues", {}).items():
            for iss in issues:
                items.append({"source": source, "category": category,
                              "title": iss.title, "url": iss.url,
                              "meta": f"labels:{','.join(iss.labels[:3])}"})

    elif source == "GeekNews":
        for g in (raw_data if isinstance(raw_data, list) else []):
            items.append({"source": source, "category": category,
                          "title": g.title, "url": g.source_url,
                          "score": g.points,
                          "body": g.summary,
                          "meta": f"domain:{g.source_domain}"})

    elif source == "Hugging Face":
        for models in raw_data.values():
            for m in models:
                items.append({"source": source, "category": category,
                              "title": m.id, "url": m.url, "score": m.downloads,
                              "meta": f"likes:{m.likes} pipeline:{m.pipeline_tag}"})

    elif source == "OSV":
        for vulns in raw_data.values():
            for v in vulns:
                items.append({"source": source, "category": category,
                              "title": f"{v.vuln_id}: {v.package} ({v.ecosystem})",
                              "meta": f"aliases:{','.join(v.aliases[:3])}"})

    return items


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

    # 수집 파이프라인 정의: (step, label, collector, category, collect_kwargs, format_kwargs)
    # category가 None이면 RSS처럼 특수 처리
    pipeline = [
        (1, "Hacker News", hn_collector, "dev",
         {"top_limit": config["hackernews"].get("top_stories", 20),
          "best_limit": config["hackernews"].get("best_stories", 10)}, {}),
        (2, "DEV.to", devto_collector, "dev",
         {"general_limit": config.get("devto", {}).get("limit", 20),
          "tags": config.get("devto", {}).get("tags")}, {}),
        (3, "Lobste.rs", lobsters_collector, "dev",
         {"hottest_limit": config.get("lobsters", {}).get("hottest", 20),
          "newest_limit": config.get("lobsters", {}).get("newest", 10)}, {}),
        (4, "RSS", rss_collector, None,  # 특수: market/dev 분리
         {"feeds_config": config["rss"].get("feeds", []),
          "items_per_feed": config["rss"].get("items_per_feed", 8)}, {}),
        (5, "GitHub Trending", github_trending_collector, "dev",
         {"limit": 10}, {}),
        (6, "GitHub API", github_api_collector, "dev",
         {"queries": config.get("github_api", {}).get("queries", []),
          "days_back": config.get("github_api", {}).get("days_back", 7),
          "per_query": config.get("github_api", {}).get("per_query", 5)}, {}),
        (7, "Claude Code", claude_code_collector, "dev",
         {"release_limit": config.get("claude_code", {}).get("release_limit", 3),
          "issue_buckets": config.get("claude_code", {}).get("issue_buckets", []),
          "issue_limit": config.get("claude_code", {}).get("issue_limit", 3)}, {}),
        (8, "GeekNews", geeknews_collector, "dev",
         {"limit": config.get("geeknews_new", {}).get("limit", 12)}, {}),
        (9, "arXiv", arxiv_collector, "dev",
         {"queries": config.get("arxiv", {}).get("queries", []),
          "per_query": config.get("arxiv", {}).get("per_query", 5)}, {}),
        (10, "OSV", osv_collector, "dev",
         {"packages": config.get("osv", {}).get("packages", []),
          "max_vulns_per_package": config.get("osv", {}).get("max_vulns_per_package", 3)}, {}),
        (11, "GDELT", gdelt_collector, "market",
         {"queries": config.get("gdelt", {}).get("queries", []),
          "max_records": config.get("gdelt", {}).get("max_records", 8),
          "timespan": config.get("gdelt", {}).get("timespan", "24h")}, {}),
        (12, "FRED", fred_collector, "market",
         {"series": config.get("fred", {}).get("series", [])}, {}),
        (13, "SEC", sec_collector, "market",
         {"companies": config.get("sec", {}).get("companies", []),
          "limit_per_company": config.get("sec", {}).get("limit_per_company", 3)}, {}),
        (14, "Treasury", treasury_collector, "market",
         {"limit": config.get("treasury", {}).get("limit", 6)}, {}),
        (15, "Hugging Face", hf_collector, "dev",
         {"trending_limit": 8, "recent_limit": 5}, {}),
    ]

    # raw 데이터 보존용
    raw_collected = {}

    for step, label, collector, category, collect_kw, format_kw in pipeline:
        print(f"\n[{step}/{total_steps}] {label} 데이터 수집 중...")
        try:
            raw_data = collector.collect_all(**collect_kw)
            raw_collected[label] = (collector, raw_data, category or "dev")

            # RSS는 market/dev 분리
            if label == "RSS":
                market_text = collector.format_for_analysis(raw_data, categories=["world", "stocks", "macro", "community"])
                dev_text = collector.format_for_analysis(raw_data, categories=["tech", "ai", "trending"])
                if market_text:
                    data_buckets["market"].append(market_text)
                if dev_text:
                    data_buckets["dev"].append(dev_text)
                # RSS는 양쪽 카테고리로 저장
                raw_collected["RSS/market"] = (collector, raw_data, "market")
                raw_collected["RSS/dev"] = (collector, raw_data, "dev")
            else:
                text = collector.format_for_analysis(raw_data, **format_kw)
                if text:
                    data_buckets[category].append(text)
        except Exception as e:
            print(f"[{label}] 수집 실패: {e}")

    # 구조화 데이터를 항목 단위로 DB 저장
    store_collected_data(storage, raw_collected)

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
