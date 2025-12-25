#!/usr/bin/env python3
"""트렌드 리포터 메인 실행 파일"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import yaml
from dotenv import load_dotenv

from cache import ContentCache
from collectors import (
    HackerNewsCollector, RSSCollector, DevToCollector, LobstersCollector,
    GitHubTrendingCollector, HuggingFaceCollector
)
from analyzer import TrendAnalyzer
from notifier import DiscordNotifier
from publisher import GitHubPagesPublisher


def load_config():
    """설정 파일 로드"""
    config_path = project_root / "config" / "sources.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


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

    # 캐시 저장
    cache.save()

    # 수집 데이터 합치기
    all_data = "\n".join(collected_data)

    # 데이터가 거의 없으면 알림만 보내고 종료
    if all_data.count("없음") >= 2 or len(all_data.strip()) < 100:
        print("\n새로운 데이터가 거의 없습니다.")
        notifier = DiscordNotifier()
        notifier.send_simple("📊 트렌드 리포트: 새로운 업데이트가 거의 없습니다.")
        return 0

    # Gemini로 분석 (두 개의 리포트 생성)
    print("\n[분석] Gemini API로 분석 중...")
    analyzer = TrendAnalyzer()
    date_str = analyzer.create_report_header()

    # 1. 세계 정세 & 주식 리포트
    print("  - 세계 정세 & 주식 리포트 생성 중...")
    world_headline, world_report = analyzer.analyze_world_market(all_data)
    world_title = f"{world_headline} | {date_str}"

    # 2. 개발 & AI 리포트
    print("  - 개발 & AI 리포트 생성 중...")
    dev_headline, dev_report = analyzer.analyze_dev_ai(all_data)
    dev_title = f"{dev_headline} | {date_str}"

    print("\n" + "=" * 50)
    print("[세계정세] " + world_title)
    print("=" * 50)
    print(world_report[:500] + "..." if len(world_report) > 500 else world_report)

    print("\n" + "=" * 50)
    print("[개발/AI] " + dev_title)
    print("=" * 50)
    print(dev_report[:500] + "..." if len(dev_report) > 500 else dev_report)

    # Discord로 전송 (두 리포트 함께)
    print("\n[전송] Discord로 리포트 전송 중...")
    notifier = DiscordNotifier()
    discord_success = notifier.send_dual_reports(
        world_title, world_report,
        dev_title, dev_report
    )

    if discord_success:
        print("✅ Discord 전송 완료!")
    else:
        print("❌ Discord 전송 실패")

    # GitHub Pages로 저장 (두 리포트 각각)
    print("\n[저장] GitHub Pages용 HTML 생성 중...")
    publisher = GitHubPagesPublisher()

    world_success = publisher.publish(world_title, world_report, category="market")
    dev_success = publisher.publish(dev_title, dev_report, category="dev")

    if world_success and dev_success:
        print("✅ GitHub Pages 저장 완료!")
    else:
        print("❌ GitHub Pages 저장 실패")

    return 0 if discord_success else 1


if __name__ == "__main__":
    sys.exit(main())
