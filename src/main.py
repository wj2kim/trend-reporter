#!/usr/bin/env python3
"""트렌드 리포터 메인 실행 파일 (Gemini 없이 원시 데이터 전송)"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pytz

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import yaml
from dotenv import load_dotenv

from cache import ContentCache
from collectors import HackerNewsCollector, RSSCollector
from notifier import DiscordNotifier


def load_config():
    """설정 파일 로드"""
    config_path = project_root / "config" / "sources.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def format_report(hn_data: dict, rss_data: dict) -> str:
    """수집된 데이터를 보기 좋게 포맷"""
    lines = []

    # Hacker News
    lines.append("**🔥 Hacker News Top Stories**")
    all_hn = hn_data.get("top", []) + hn_data.get("best", [])
    all_hn.sort(key=lambda x: x.score, reverse=True)

    for i, story in enumerate(all_hn[:10], 1):
        lines.append(f"{i}. [{story.title}]({story.url})")
        lines.append(f"   ⬆️ {story.score} pts | 💬 {story.num_comments}")

    lines.append("")
    lines.append("**📰 Tech News (RSS)**")

    # RSS
    all_rss = []
    for category, items in rss_data.items():
        all_rss.extend(items)
    all_rss.sort(key=lambda x: x.published, reverse=True)

    for i, item in enumerate(all_rss[:10], 1):
        lines.append(f"{i}. [{item.title}]({item.url})")
        lines.append(f"   📌 {item.source}")

    return "\n".join(lines)


def main():
    """메인 실행 함수"""
    # 환경변수 로드
    load_dotenv(project_root / ".env")

    print("=" * 50)
    print("트렌드 리포터 시작 (원시 데이터 모드)")
    print("=" * 50)

    # 설정 로드
    config = load_config()

    # 캐시 초기화
    cache = ContentCache(cache_dir=str(project_root / "cache"))

    # 1. Hacker News 수집
    print("\n[1/2] Hacker News 데이터 수집 중...")
    hn_data = {"top": [], "best": []}
    try:
        hn_collector = HackerNewsCollector(cache=cache)
        hn_data = hn_collector.collect_all(
            top_limit=config["hackernews"].get("top_stories", 20),
            best_limit=config["hackernews"].get("best_stories", 10)
        )
    except Exception as e:
        print(f"[HN] 수집 실패: {e}")

    # 2. RSS 수집
    print("\n[2/2] RSS 피드 수집 중...")
    rss_data = {}
    try:
        rss_collector = RSSCollector(cache=cache)
        rss_data = rss_collector.collect_all(
            feeds_config=config["rss"].get("feeds", []),
            items_per_feed=config["rss"].get("items_per_feed", 8)
        )
    except Exception as e:
        print(f"[RSS] 수집 실패: {e}")

    # 캐시 저장
    cache.save()

    # 수집된 데이터 확인
    total_hn = len(hn_data.get("top", [])) + len(hn_data.get("best", []))
    total_rss = sum(len(items) for items in rss_data.values())

    print(f"\n수집 완료: HN {total_hn}개, RSS {total_rss}개")

    # 데이터가 없으면 간단한 알림
    if total_hn == 0 and total_rss == 0:
        print("\n새로운 데이터가 없습니다.")
        notifier = DiscordNotifier()
        notifier.send_simple("📊 트렌드 리포트: 새로운 업데이트가 없습니다.")
        return 0

    # 리포트 포맷
    report = format_report(hn_data, rss_data)

    # 타임스탬프
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    title = f"📊 트렌드 리포트 | {now_kst.strftime('%Y-%m-%d %H:%M')} KST"

    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)
    print(report[:500] + "..." if len(report) > 500 else report)

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
