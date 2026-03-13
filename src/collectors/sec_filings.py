"""SEC EDGAR 최근 공시 수집기"""

import os
from dataclasses import dataclass
from typing import List, Optional

import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cache import ContentCache


SEC_BASE_URL = "https://data.sec.gov/submissions"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


@dataclass
class SECFiling:
    """SEC 공시 데이터"""
    company: str
    ticker: str
    form: str
    filing_date: str
    accession_number: str
    primary_document: str
    url: str


class SECFilingsCollector:
    """SEC submissions JSON을 사용한 최근 공시 수집"""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": os.getenv(
                "SEC_USER_AGENT",
                "TrendReporter/1.0 trend-reporter@example.com",
            )
        })
        self.cache = cache

    def collect_company(self, company_cfg: dict, limit: int = 5) -> List[SECFiling]:
        """단일 회사의 최근 공시 수집"""
        cik = str(company_cfg["cik"]).zfill(10)
        try:
            resp = self.session.get(f"{SEC_BASE_URL}/CIK{cik}.json", timeout=20)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"[SEC] {company_cfg.get('ticker', cik)} 수집 실패: {e}")
            return []

        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_documents = recent.get("primaryDocument", [])

        desired_forms = set(company_cfg.get("forms", []))
        filings = []

        for form, accession, filing_date, primary_doc in zip(
            forms,
            accession_numbers,
            filing_dates,
            primary_documents,
        ):
            if desired_forms and form not in desired_forms:
                continue

            cache_id = f"sec_{cik}_{accession}"
            if self.cache and self.cache.is_seen(cache_id):
                continue

            accession_plain = accession.replace("-", "")
            archive_cik = str(int(cik))
            url = f"{SEC_ARCHIVES_BASE}/{archive_cik}/{accession_plain}/{primary_doc}"

            filings.append(SECFiling(
                company=company_cfg.get("name", company_cfg.get("ticker", cik)),
                ticker=company_cfg.get("ticker", ""),
                form=form,
                filing_date=filing_date,
                accession_number=accession,
                primary_document=primary_doc,
                url=url,
            ))

            if self.cache:
                self.cache.mark_seen(cache_id)

            if len(filings) >= limit:
                break

        return filings

    def collect_all(self, companies: List[dict], limit_per_company: int = 3) -> dict:
        """설정된 회사들의 최근 공시 수집"""
        results = {}
        total = 0

        for company_cfg in companies:
            ticker = company_cfg.get("ticker", company_cfg.get("cik", "unknown"))
            filings = self.collect_company(company_cfg, limit=limit_per_company)
            results[ticker] = filings
            total += len(filings)
            print(f"[SEC] {ticker}: {len(filings)}개 공시 수집")

        print(f"[SEC] 총 {total}개 공시 수집")
        return results

    def format_for_analysis(self, data: dict) -> str:
        """분석용 텍스트 포맷"""
        output = []
        total = 0

        for ticker, filings in data.items():
            if not filings:
                continue

            output.append(f"\n## SEC Filings - {ticker}\n")
            for i, filing in enumerate(filings, 1):
                output.append(
                    f"{i}. {filing.company} {filing.form}\n"
                    f"   Filing Date: {filing.filing_date}\n"
                    f"   URL: {filing.url}\n"
                )
                total += 1

        if total == 0:
            return "[SEC] 새로운 공시 없음\n"

        return "\n".join(output)
