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
from collectors import (
    HackerNewsCollector, RSSCollector, DevToCollector, LobstersCollector,
    GitHubTrendingCollector, HuggingFaceCollector,
    # 커뮤니티 수집기
    ClienCollector, DCInsideCollector,
    PpomppuCollector, RuliwebCollector, FiveChCollector
)
from analyzer import TrendAnalyzer
from notifier import DiscordNotifier
from publisher import GitHubPagesPublisher


def load_config():
    """설정 파일 로드"""
    config_path = project_root / "config" / "sources.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_previous_reports(limit: int = 10) -> dict:
    """이전 리포트 제목 로드 (중복 방지용)"""
    reports_json = project_root / "docs" / "reports.json"
    previous = {"market": [], "dev": [], "community": []}

    if not reports_json.exists():
        return previous

    try:
        with open(reports_json, 'r', encoding='utf-8') as f:
            reports = json.load(f)

        for r in reports[:limit * 3]:  # 각 카테고리별로 limit개씩
            category = r.get("category", "")
            title = r.get("title", "").split(" | ")[0]  # 날짜 부분 제거
            if category == "market" and len(previous["market"]) < limit:
                previous["market"].append(title)
            elif category == "dev" and len(previous["dev"]) < limit:
                previous["dev"].append(title)
            elif category == "community" and len(previous["community"]) < limit:
                previous["community"].append(title)

        print(f"[중복방지] 이전 리포트 로드: Market {len(previous['market'])}개, Dev {len(previous['dev'])}개, Community {len(previous['community'])}개")
    except Exception as e:
        print(f"[중복방지] 이전 리포트 로드 실패: {e}")

    return previous


def main():
    """메인 실행 함수"""
    # 환경변수 로드
    load_dotenv(project_root / ".env")

    print("=" * 50)
    print("트렌드 리포터 시작")
    print("=" * 50)

    # 설정 로드
    config = load_config()

    # 캐시 초기화
    cache = ContentCache(cache_dir=str(project_root / "cache"))

    # 수집된 데이터 저장
    collected_data = []

    # 1. Hacker News 수집
    print("\n[1/6] Hacker News 데이터 수집 중...")
    try:
        hn_collector = HackerNewsCollector(cache=cache)
        hn_data = hn_collector.collect_all(
            top_limit=config["hackernews"].get("top_stories", 20),
            best_limit=config["hackernews"].get("best_stories", 10)
        )
        collected_data.append(hn_collector.format_for_analysis(hn_data))
    except Exception as e:
        print(f"[HN] 수집 실패: {e}")
        collected_data.append("[HN] 수집 실패\n")

    # 2. DEV.to 수집
    print("\n[2/6] DEV.to 데이터 수집 중...")
    try:
        devto_collector = DevToCollector(cache=cache)
        devto_data = devto_collector.collect_all(
            general_limit=config.get("devto", {}).get("limit", 20),
            tags=config.get("devto", {}).get("tags")
        )
        collected_data.append(devto_collector.format_for_analysis(devto_data))
    except Exception as e:
        print(f"[DEV.to] 수집 실패: {e}")
        collected_data.append("[DEV.to] 수집 실패\n")

    # 3. Lobste.rs 수집
    print("\n[3/6] Lobste.rs 데이터 수집 중...")
    try:
        lobsters_collector = LobstersCollector(cache=cache)
        lobsters_data = lobsters_collector.collect_all(
            hottest_limit=config.get("lobsters", {}).get("hottest", 20),
            newest_limit=config.get("lobsters", {}).get("newest", 10)
        )
        collected_data.append(lobsters_collector.format_for_analysis(lobsters_data))
    except Exception as e:
        print(f"[Lobsters] 수집 실패: {e}")
        collected_data.append("[Lobsters] 수집 실패\n")

    # 4. RSS 수집
    print("\n[4/6] RSS 피드 수집 중...")
    try:
        rss_collector = RSSCollector(cache=cache)
        rss_data = rss_collector.collect_all(
            feeds_config=config["rss"].get("feeds", []),
            items_per_feed=config["rss"].get("items_per_feed", 8)
        )
        collected_data.append(rss_collector.format_for_analysis(rss_data))
    except Exception as e:
        print(f"[RSS] 수집 실패: {e}")
        collected_data.append("[RSS] 수집 실패\n")

    # 5. GitHub Trending 수집
    print("\n[5/6] GitHub Trending 수집 중...")
    try:
        github_collector = GitHubTrendingCollector(cache=cache)
        github_data = github_collector.collect_all(limit=10)
        collected_data.append(github_collector.format_for_analysis(github_data))
    except Exception as e:
        print(f"[GitHub] 수집 실패: {e}")
        collected_data.append("[GitHub] 수집 실패\n")

    # 6. Hugging Face 수집
    print("\n[6/6] Hugging Face 모델 수집 중...")
    try:
        hf_collector = HuggingFaceCollector(cache=cache)
        hf_data = hf_collector.collect_all(trending_limit=8, recent_limit=5)
        collected_data.append(hf_collector.format_for_analysis(hf_data))
    except Exception as e:
        print(f"[HuggingFace] 수집 실패: {e}")
        collected_data.append("[HuggingFace] 수집 실패\n")

    # 커뮤니티 수집 (별도 데이터)
    print("\n" + "=" * 50)
    print("커뮤니티 데이터 수집")
    print("=" * 50)
    community_data = []

    # 7. 클리앙
    print("\n[Community 1/6] 클리앙 수집 중...")
    try:
        clien_collector = ClienCollector(cache=cache)
        clien_posts = clien_collector.collect_posts(limit=15)
        community_data.append(clien_collector.format_for_analysis(clien_posts))
    except Exception as e:
        print(f"[Clien] 수집 실패: {e}")
        community_data.append("[클리앙] 수집 실패\n")

    # 8. 디시인사이드
    print("\n[Community 2/6] 디시인사이드 수집 중...")
    try:
        dc_collector = DCInsideCollector(cache=cache)
        dc_posts = dc_collector.collect_posts(limit=15)
        community_data.append(dc_collector.format_for_analysis(dc_posts))
    except Exception as e:
        print(f"[DCInside] 수집 실패: {e}")
        community_data.append("[디시인사이드] 수집 실패\n")

    # 9. 뽐뿌
    print("\n[Community 3/5] 뽐뿌 수집 중...")
    try:
        ppomppu_collector = PpomppuCollector(cache=cache)
        ppomppu_posts = ppomppu_collector.collect_posts(limit=15)
        community_data.append(ppomppu_collector.format_for_analysis(ppomppu_posts))
    except Exception as e:
        print(f"[Ppomppu] 수집 실패: {e}")
        community_data.append("[뽐뿌] 수집 실패\n")

    # 10. 루리웹
    print("\n[Community 4/5] 루리웹 수집 중...")
    try:
        ruliweb_collector = RuliwebCollector(cache=cache)
        ruliweb_posts = ruliweb_collector.collect_posts(limit=15)
        community_data.append(ruliweb_collector.format_for_analysis(ruliweb_posts))
    except Exception as e:
        print(f"[Ruliweb] 수집 실패: {e}")
        community_data.append("[루리웹] 수집 실패\n")

    # 11. 5ch
    print("\n[Community 5/5] 5ch 수집 중...")
    try:
        fivech_collector = FiveChCollector(cache=cache)
        fivech_posts = fivech_collector.collect_posts(limit=15)
        community_data.append(fivech_collector.format_for_analysis(fivech_posts))
    except Exception as e:
        print(f"[5ch] 수집 실패: {e}")
        community_data.append("[5ch] 수집 실패\n")

    # 주식 커뮤니티 수집 (Market 리포트에 추가)
    print("\n" + "=" * 50)
    print("주식 커뮤니티 데이터 수집")
    print("=" * 50)
    stock_community_data = []

    # 디시인사이드 주식갤러리
    print("\n[Stock 1/2] 디시인사이드 주식갤러리 수집 중...")
    try:
        dc_stock_posts = dc_collector.collect_stock_posts(limit_per_gallery=10)
        stock_community_data.append(dc_collector.format_stock_for_analysis(dc_stock_posts))
    except Exception as e:
        print(f"[DCInside Stock] 수집 실패: {e}")

    # 뽐뿌 주식/코인
    print("\n[Stock 2/2] 뽐뿌 주식/코인 수집 중...")
    try:
        ppomppu_stock_posts = ppomppu_collector.collect_stock_posts(limit_per_board=10)
        stock_community_data.append(ppomppu_collector.format_stock_for_analysis(ppomppu_stock_posts))
    except Exception as e:
        print(f"[Ppomppu Stock] 수집 실패: {e}")

    # 주식 커뮤니티 데이터를 메인 데이터에 추가 (Market 리포트용)
    if stock_community_data:
        collected_data.append("\n\n## 주식 커뮤니티 여론\n")
        collected_data.extend(stock_community_data)

    # 캐시 저장
    cache.save()

    # 수집 데이터 합치기
    all_data = "\n".join(collected_data)

    # 메인 데이터(HN, DEV.to, RSS 등)가 거의 없으면 알림만 보내고 종료
    # 주식/커뮤니티 수집 실패는 무시 (보조 데이터)
    main_data_length = len(all_data.split("## 주식 커뮤니티")[0].strip())
    if main_data_length < 500:
        print("\n새로운 데이터가 거의 없습니다.")
        notifier = DiscordNotifier()
        notifier.send_simple("📊 트렌드 리포트: 새로운 업데이트가 거의 없습니다.")
        return 0

    # 이전 리포트 로드 (중복 방지)
    previous_reports = load_previous_reports(limit=5)

    # Gemini로 분석 (두 개의 리포트 생성)
    print("\n[분석] Gemini API로 분석 중...")
    analyzer = TrendAnalyzer()
    date_str = analyzer.create_report_header()

    # 1. 세계 정세 & 주식 리포트
    print("  - 세계 정세 & 주식 리포트 생성 중...")
    world_headline, world_keywords, world_report = analyzer.analyze_world_market(
        all_data,
        previous_titles=previous_reports["market"]
    )
    world_title = f"{world_headline} | {date_str}"

    # 2. 개발 & AI 리포트
    print("  - 개발 & AI 리포트 생성 중...")
    dev_headline, dev_keywords, dev_report = analyzer.analyze_dev_ai(
        all_data,
        previous_titles=previous_reports["dev"]
    )
    dev_title = f"{dev_headline} | {date_str}"

    # 3. 커뮤니티 리포트 (별도 데이터 사용)
    all_community_data = "\n".join(community_data)
    community_title = ""
    community_report = ""

    if all_community_data.count("수집 실패") < 4:  # 최소 3개 이상 성공
        print("  - 커뮤니티 리포트 생성 중...")
        community_headline, community_keywords, community_report = analyzer.analyze_community(
            all_community_data,
            previous_titles=previous_reports.get("community", [])
        )
        community_title = f"{community_headline} | {date_str}"
    else:
        print("  - 커뮤니티 데이터 부족, 리포트 생략")

    print("\n" + "=" * 50)
    print("[세계정세] " + world_title)
    print("=" * 50)
    print(world_report[:500] + "..." if len(world_report) > 500 else world_report)

    print("\n" + "=" * 50)
    print("[개발/AI] " + dev_title)
    print("=" * 50)
    print(dev_report[:500] + "..." if len(dev_report) > 500 else dev_report)

    if community_report:
        print("\n" + "=" * 50)
        print("[커뮤니티] " + community_title)
        print("=" * 50)
        print(community_report[:500] + "..." if len(community_report) > 500 else community_report)

    # Discord로 전송
    print("\n[전송] Discord로 리포트 전송 중...")
    notifier = DiscordNotifier()

    # Market, Dev 리포트 전송
    discord_success = notifier.send_dual_reports(
        world_title, world_report,
        dev_title, dev_report
    )

    # 커뮤니티 리포트 별도 전송 (있을 경우)
    if community_report:
        community_discord_success = notifier.send_community_report(
            community_title, community_report
        )
        if community_discord_success:
            print("✅ 커뮤니티 리포트 Discord 전송 완료!")
        else:
            print("❌ 커뮤니티 리포트 Discord 전송 실패")

    if discord_success:
        print("✅ Discord 전송 완료!")
    else:
        print("❌ Discord 전송 실패")

    # GitHub Pages로 저장 (Market, Dev만 - 커뮤니티는 제외)
    print("\n[저장] GitHub Pages용 HTML 생성 중...")
    publisher = GitHubPagesPublisher()

    world_success = publisher.publish(world_title, world_report, category="market", keywords=world_keywords)
    dev_success = publisher.publish(dev_title, dev_report, category="dev", keywords=dev_keywords)

    if world_success and dev_success:
        print("✅ GitHub Pages 저장 완료!")
    else:
        print("❌ GitHub Pages 저장 실패")

    return 0 if discord_success else 1


if __name__ == "__main__":
    sys.exit(main())
