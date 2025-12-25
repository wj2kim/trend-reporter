"""Hugging Face 트렌딩 모델 수집기"""

import os
import requests
from typing import List, Optional
from dataclasses import dataclass

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


HF_API_BASE = "https://huggingface.co/api"


@dataclass
class HFModel:
    """Hugging Face 모델 데이터"""
    id: str
    author: str
    name: str
    downloads: int
    likes: int
    pipeline_tag: str
    tags: List[str]
    url: str


class HuggingFaceCollector:
    """Hugging Face Hub에서 트렌딩 모델을 수집하는 클래스"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.cache = cache

    def collect_trending_models(self, limit: int = 15) -> List[HFModel]:
        """트렌딩 모델 수집 (다운로드순)"""
        url = f"{HF_API_BASE}/models"
        params = {
            "sort": "downloads",
            "direction": -1,
            "limit": limit * 2,  # 캐시 고려
            "full": "true"
        }

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[HuggingFace] 모델 목록 요청 실패: {e}")
            return []

        models = []
        for item in data:
            model_id = item.get("id", "")

            # 캐시된 모델 스킵
            cache_id = f"hf_{model_id}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            # author/name 분리
            parts = model_id.split("/")
            author = parts[0] if len(parts) > 1 else ""
            name = parts[-1]

            models.append(HFModel(
                id=model_id,
                author=author,
                name=name,
                downloads=item.get("downloads", 0),
                likes=item.get("likes", 0),
                pipeline_tag=item.get("pipeline_tag", ""),
                tags=item.get("tags", [])[:5],
                url=f"https://huggingface.co/{model_id}"
            ))

            # 캐시에 추가
            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(models) >= limit:
                break

        return models

    def collect_recent_models(self, limit: int = 10) -> List[HFModel]:
        """최근 업데이트된 인기 모델 수집"""
        url = f"{HF_API_BASE}/models"
        params = {
            "sort": "lastModified",
            "direction": -1,
            "limit": limit * 3,
            "full": "true"
        }

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[HuggingFace] 최근 모델 요청 실패: {e}")
            return []

        models = []
        for item in data:
            # 다운로드가 일정 수 이상인 것만
            if item.get("downloads", 0) < 1000:
                continue

            model_id = item.get("id", "")

            cache_id = f"hf_recent_{model_id}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            parts = model_id.split("/")
            author = parts[0] if len(parts) > 1 else ""
            name = parts[-1]

            models.append(HFModel(
                id=model_id,
                author=author,
                name=name,
                downloads=item.get("downloads", 0),
                likes=item.get("likes", 0),
                pipeline_tag=item.get("pipeline_tag", ""),
                tags=item.get("tags", [])[:5],
                url=f"https://huggingface.co/{model_id}"
            ))

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(models) >= limit:
                break

        return models

    def collect_all(self, trending_limit: int = 10, recent_limit: int = 5) -> dict:
        """트렌딩과 최근 모델 모두 수집"""
        results = {
            "trending": self.collect_trending_models(trending_limit),
            "recent": self.collect_recent_models(recent_limit)
        }

        # 중복 제거
        trending_ids = {m.id for m in results["trending"]}
        results["recent"] = [m for m in results["recent"] if m.id not in trending_ids]

        total = len(results["trending"]) + len(results["recent"])
        print(f"[HuggingFace] 총 {total}개 모델 수집")

        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석을 위한 텍스트 포맷"""
        output = ["\n## Hugging Face AI Models\n"]

        trending = data.get("trending", [])
        recent = data.get("recent", [])

        if not trending and not recent:
            return "[HuggingFace] 새로운 모델 없음\n"

        if trending:
            output.append("### 인기 AI 모델 (다운로드 순)\n")
            for i, model in enumerate(trending[:8], 1):
                pipeline = f"[{model.pipeline_tag}] " if model.pipeline_tag else ""
                output.append(
                    f"{i}. {pipeline}{model.id}\n"
                    f"   Downloads: {model.downloads:,} | Likes: {model.likes:,}\n"
                    f"   Tags: {', '.join(model.tags[:3])}\n"
                )

        if recent:
            output.append("\n### 최근 업데이트된 모델\n")
            for model in recent[:5]:
                pipeline = f"[{model.pipeline_tag}] " if model.pipeline_tag else ""
                output.append(
                    f"- {pipeline}{model.id} (Downloads: {model.downloads:,})\n"
                )

        return "\n".join(output)
