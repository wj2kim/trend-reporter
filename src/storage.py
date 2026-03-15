"""수집 데이터 영구 저장소 (SQLite + FTS5)

2단계 조회 패턴으로 컨텍스트/토큰 사용 최소화:
  Step 1: browse() — 제목+메타만 반환 (~50 bytes/항목)
  Step 2: get_detail() — 필요한 항목의 body만 반환
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import pytz


class TrendStorage:

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "trends.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT DEFAULT '',
                score INTEGER DEFAULT 0,
                body TEXT DEFAULT '',
                meta TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_items_date ON items(date);
            CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
            CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);

            CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                title, body, source, category,
                content='items', content_rowid='id',
                tokenize='unicode61'
            );

            CREATE TRIGGER IF NOT EXISTS items_fts_ai AFTER INSERT ON items BEGIN
                INSERT INTO items_fts(rowid, title, body, source, category)
                VALUES (new.id, new.title, new.body, new.source, new.category);
            END;

            CREATE TRIGGER IF NOT EXISTS items_fts_ad AFTER DELETE ON items BEGIN
                INSERT INTO items_fts(items_fts, rowid, title, body, source, category)
                VALUES ('delete', old.id, old.title, old.body, old.source, old.category);
            END;
        """)
        self.db.commit()

    # ── 저장 ──

    def save_item(self, source: str, category: str, title: str,
                  url: str = "", score: int = 0, body: str = "", meta: str = ""):
        """개별 항목 저장"""
        if not title or not title.strip():
            return
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        self.db.execute(
            "INSERT INTO items (date, source, category, title, url, score, body, meta, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (now.strftime("%Y-%m-%d"), source, category, title.strip(),
             url.strip(), score, body.strip(), meta.strip(), now.isoformat())
        )

    def save_items(self, items: list):
        """여러 항목 일괄 저장. items: list of dict with keys matching save_item params"""
        for item in items:
            self.save_item(**item)
        self.db.commit()

    def flush(self):
        """버퍼 커밋"""
        self.db.commit()

    # ── Step 1: 가벼운 조회 (제목+메타만, 컨텍스트 최소) ──

    def browse(self, date_from: str = None, date_to: str = None,
               category: str = None, source: str = None, limit: int = 50) -> list:
        """제목+메타 목록 반환. body 제외로 컨텍스트 절약."""
        conditions = []
        params = []

        if date_from:
            conditions.append("date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("date <= ?")
            params.append(date_to)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if source:
            conditions.append("source = ?")
            params.append(source)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        rows = self.db.execute(f"""
            SELECT id, date, source, category, title, score
            FROM items {where}
            ORDER BY date DESC, score DESC
            LIMIT ?
        """, params).fetchall()

        return [{"id": r[0], "date": r[1], "source": r[2], "category": r[3],
                 "title": r[4], "score": r[5]} for r in rows]

    def search(self, query: str, limit: int = 20, category: str = None) -> list:
        """FTS 키워드 검색. 제목 snippet만 반환."""
        conditions = ["items_fts MATCH ?"]
        params = [query]
        if category:
            conditions.append("category = ?")
            params.append(category)

        where = " AND ".join(conditions)
        params.append(limit)

        rows = self.db.execute(f"""
            SELECT i.id, i.date, i.source, i.category,
                   snippet(items_fts, 0, '>>>', '<<<', '...', 32),
                   i.score
            FROM items_fts
            JOIN items i ON i.id = items_fts.rowid
            WHERE {where}
            ORDER BY rank
            LIMIT ?
        """, params).fetchall()

        return [{"id": r[0], "date": r[1], "source": r[2], "category": r[3],
                 "title_snippet": r[4], "score": r[5]} for r in rows]

    # ── Step 2: 상세 조회 (필요한 항목만) ──

    def get_detail(self, item_ids: list) -> list:
        """특정 항목의 전체 데이터 (body 포함) 반환."""
        if not item_ids:
            return []
        placeholders = ",".join("?" * len(item_ids))
        rows = self.db.execute(f"""
            SELECT id, date, source, category, title, url, score, body, meta
            FROM items WHERE id IN ({placeholders})
            ORDER BY date DESC, score DESC
        """, item_ids).fetchall()

        return [{"id": r[0], "date": r[1], "source": r[2], "category": r[3],
                 "title": r[4], "url": r[5], "score": r[6], "body": r[7], "meta": r[8]}
                for r in rows]

    # ── 유틸리티 ──

    def stats(self) -> dict:
        """DB 요약 통계"""
        row = self.db.execute("""
            SELECT MIN(date), MAX(date), COUNT(*),
                   COUNT(DISTINCT source), COUNT(DISTINCT date)
            FROM items
        """).fetchone()
        return {
            "date_from": row[0], "date_to": row[1],
            "total_items": row[2], "sources": row[3], "days": row[4]
        }

    def close(self):
        self.db.close()
