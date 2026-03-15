"""기사 본문에서 핵심 문장을 추출하는 유틸리티"""

import re
import requests
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed


class _TextExtractor(HTMLParser):
    """HTML에서 <p> 태그 텍스트만 추출"""

    SKIP_TAGS = {'script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe'}

    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self._current = []
        self._in_p = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag == 'p' and self._skip_depth == 0:
            self._in_p = True
            self._current = []

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == 'p' and self._in_p:
            text = ' '.join(''.join(self._current).split()).strip()
            if len(text) > 40:
                self.paragraphs.append(text)
            self._in_p = False

    def handle_data(self, data):
        if self._in_p and self._skip_depth == 0:
            self._current.append(data)


def _split_sentences(text: str) -> list:
    """텍스트를 문장 단위로 분리"""
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 20]


def _has_data(sentence: str) -> bool:
    """숫자/퍼센트/금액 등 데이터가 포함된 문장인지"""
    return bool(re.search(r'\d+[\.,]?\d*\s*[%$€₩billion|million|조|억|만]|\d{1,3}(?:,\d{3})+', sentence, re.IGNORECASE))


def extract_key_sentences(url: str, max_sentences: int = 5, timeout: int = 5) -> str:
    """URL에서 핵심 문장 추출.

    전략:
    1. 첫 3문장 (역피라미드 구조 활용)
    2. 숫자/데이터가 있는 문장 우선 추가
    """
    try:
        resp = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'TrendReporter/1.0 (article summary extraction)'
        })
        resp.raise_for_status()

        parser = _TextExtractor()
        parser.feed(resp.text)

        if not parser.paragraphs:
            return ""

        all_sentences = []
        for p in parser.paragraphs[:10]:
            all_sentences.extend(_split_sentences(p))

        if not all_sentences:
            return ""

        # 첫 3문장
        result = all_sentences[:3]

        # 데이터 포함 문장 추가 (중복 제외)
        for s in all_sentences[3:]:
            if len(result) >= max_sentences:
                break
            if _has_data(s) and s not in result:
                result.append(s)

        return ' '.join(result)

    except Exception:
        return ""


def extract_batch(urls: list, max_sentences: int = 5, timeout: int = 5, max_workers: int = 8) -> dict:
    """여러 URL을 병렬로 추출. {url: extracted_text} 반환."""
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(extract_key_sentences, url, max_sentences, timeout): url
            for url in urls if url
        }
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception:
                results[url] = ""

    return results
