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
from collectors import RedditCollector, HackerNewsCollector, RSSCollector
from analyzer import TrendAnalyzer
from notifier import SlackNotifier


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

    # 1. Reddit 수집
    print("\n[1/3] Reddit 데이터 수집 중...")
    try:
        reddit_collector = RedditCollector(cache=cache)
        reddit_categories = {
            k: v for k, v in config["reddit"].items()
            if isinstance(v, list)
        }
        reddit_data = reddit_collector.collect_by_category(
            reddit_categories,
            posts_per_subreddit=config["reddit"].get("posts_per_subreddit", 15),
            sort_by=config["reddit"].get("sort_by", "hot")
        )
        collected_data.append(reddit_collector.format_for_analysis(reddit_data))
    except Exception as e:
        print(f"[Reddit] 수집 실패: {e}")
        collected_data.append("[Reddit] 수집 실패\n")

    # 2. Hacker News 수집
    print("\n[2/3] Hacker News 데이터 수집 중...")
    try:
        hn_collector = HackerNewsCollector(cache=cache)
        hn_data = hn_collector.collect_all(
            top_limit=config["hackernews"].get("top_stories", 30),
            best_limit=config["hackernews"].get("best_stories", 20)
        )
        collected_data.append(hn_collector.format_for_analysis(hn_data))
    except Exception as e:
        print(f"[HN] 수집 실패: {e}")
        collected_data.append("[HN] 수집 실패\n")

    # 3. RSS 수집
    print("\n[3/3] RSS 피드 수집 중...")
    try:
        rss_collector = RSSCollector(cache=cache)
        rss_data = rss_collector.collect_all(
            feeds_config=config["rss"].get("feeds", []),
            items_per_feed=config["rss"].get("items_per_feed", 10)
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
    if "새로운" in all_data and all_data.count("없음") >= 3:
        print("\n새로운 데이터가 거의 없습니다. 간단한 알림만 전송합니다.")
        notifier = SlackNotifier()
        notifier.send_simple("📊 트렌드 리포트: 새로운 업데이트가 거의 없습니다.")
        return

    # Claude로 분석
    print("\n[분석] Claude API로 분석 중...")
    analyzer = TrendAnalyzer()
    report = analyzer.analyze(all_data)
    title = analyzer.create_report_header()

    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)
    print(report)

    # Slack으로 전송
    print("\n[전송] Slack으로 리포트 전송 중...")
    notifier = SlackNotifier()
    success = notifier.send(title, report)

    if success:
        print("\n✅ 리포트 전송 완료!")
    else:
        print("\n❌ 리포트 전송 실패")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
