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
from collectors import HackerNewsCollector, RSSCollector
from analyzer import TrendAnalyzer
from notifier import DiscordNotifier


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
    print("\n[1/2] Hacker News 데이터 수집 중...")
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

    # 2. RSS 수집
    print("\n[2/2] RSS 피드 수집 중...")
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

    # Gemini로 분석
    print("\n[분석] Gemini API로 분석 중...")
    analyzer = TrendAnalyzer()
    report = analyzer.analyze(all_data)
    title = analyzer.create_report_header()

    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)
    print(report[:1000] + "..." if len(report) > 1000 else report)

    # Discord로 전송
    print("\n[전송] Discord로 리포트 전송 중...")
    notifier = DiscordNotifier()
    success = notifier.send(title, report)

    if success:
        print("\n✅ 리포트 전송 완료!")
    else:
        print("\n❌ 리포트 전송 실패")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
