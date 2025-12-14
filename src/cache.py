"""수집된 컨텐츠 캐시 관리"""

import json
import os
from datetime import datetime, timedelta
from typing import Set
from pathlib import Path


class ContentCache:
    """이미 수집한 컨텐츠를 추적하여 중복 수집 방지"""

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "seen_content.json"
        self._load_cache()

    def _load_cache(self):
        """캐시 파일 로드"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                self.seen_ids = set(data.get("ids", []))
                self.last_cleanup = datetime.fromisoformat(
                    data.get("last_cleanup", datetime.now().isoformat())
                )
        else:
            self.seen_ids: Set[str] = set()
            self.last_cleanup = datetime.now()

    def _save_cache(self):
        """캐시 파일 저장"""
        with open(self.cache_file, 'w') as f:
            json.dump({
                "ids": list(self.seen_ids),
                "last_cleanup": self.last_cleanup.isoformat()
            }, f)

    def is_seen(self, content_id: str) -> bool:
        """이미 본 컨텐츠인지 확인"""
        return content_id in self.seen_ids

    def mark_seen(self, content_id: str):
        """컨텐츠를 본 것으로 표시"""
        self.seen_ids.add(content_id)

    def cleanup_old(self, days: int = 3):
        """오래된 캐시 정리 (3일 이상)"""
        if datetime.now() - self.last_cleanup > timedelta(days=1):
            # 캐시 크기가 10000개 이상이면 절반으로 줄임
            if len(self.seen_ids) > 10000:
                self.seen_ids = set(list(self.seen_ids)[-5000:])
            self.last_cleanup = datetime.now()

    def save(self):
        """캐시 저장 및 정리"""
        self.cleanup_old()
        self._save_cache()
