"""수집 데이터 영구 저장소 (SQLite + FTS5)"""

import sqlite3
from datetime import datetime
from pathlib import Path
import pytz


class TrendStorage:
    """수집된 트렌드 데이터를 SQLite에 저장하고 검색하는 클래스"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "trends.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS collected (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_collected_date ON collected(date);
            CREATE INDEX IF NOT EXISTS idx_collected_source ON collected(source);
            CREATE INDEX IF NOT EXISTS idx_collected_category ON collected(category);

            CREATE VIRTUAL TABLE IF NOT EXISTS collected_fts USING fts5(
                source, category, content,
                content='collected', content_rowid='id',
                tokenize='unicode61'
            );

            CREATE TRIGGER IF NOT EXISTS collected_ai AFTER INSERT ON collected BEGIN
                INSERT INTO collected_fts(rowid, source, category, content)
                VALUES (new.id, new.source, new.category, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS collected_ad AFTER DELETE ON collected BEGIN
                INSERT INTO collected_fts(collected_fts, rowid, source, category, content)
                VALUES ('delete', old.id, old.source, old.category, old.content);
            END;
        """)
        self.db.commit()

    def save(self, source: str, category: str, content: str):
        """수집 데이터 저장"""
        if not content or not content.strip():
            return
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        self.db.execute(
            "INSERT INTO collected (date, source, category, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (now.strftime("%Y-%m-%d"), source, category, content, now.isoformat())
        )
        self.db.commit()

    def search(self, query: str, limit: int = 10, days_back: int = None, category: str = None) -> list:
        """FTS5 전문 검색. 컨텍스트 절약을 위해 snippet 반환."""
        conditions = ["collected_fts MATCH ?"]
        params = [query]

        if days_back:
            conditions.append("date >= date('now', ?)")
            params.append(f"-{days_back} days")
        if category:
            conditions.append("category = ?")
            params.append(category)

        where = " AND ".join(conditions)
        params.append(limit)

        rows = self.db.execute(f"""
            SELECT c.date, c.source, c.category,
                   snippet(collected_fts, 2, '>>>', '<<<', '...', 64)
            FROM collected_fts
            JOIN collected c ON c.id = collected_fts.rowid
            WHERE {where}
            ORDER BY rank
            LIMIT ?
        """, params).fetchall()

        return [{"date": r[0], "source": r[1], "category": r[2], "snippet": r[3]} for r in rows]

    def get_by_date(self, date: str, source: str = None, category: str = None) -> list:
        """특정 날짜의 수집 데이터 조회"""
        conditions = ["date = ?"]
        params = [date]
        if source:
            conditions.append("source = ?")
            params.append(source)
        if category:
            conditions.append("category = ?")
            params.append(category)

        rows = self.db.execute(
            f"SELECT date, source, category, content FROM collected WHERE {' AND '.join(conditions)} ORDER BY source",
            params
        ).fetchall()

        return [{"date": r[0], "source": r[1], "category": r[2], "content": r[3]} for r in rows]

    def get_sources(self) -> list:
        """저장된 소스 목록"""
        return [r[0] for r in self.db.execute("SELECT DISTINCT source FROM collected ORDER BY source").fetchall()]

    def get_date_range(self) -> dict:
        """저장된 데이터의 날짜 범위"""
        row = self.db.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM collected").fetchone()
        return {"min_date": row[0], "max_date": row[1], "total_records": row[2]}

    def close(self):
        self.db.close()
