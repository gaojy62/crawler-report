"""
Cache and deduplication using SQLite
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from crawler.base import CrawledItem


class Cache:
    """SQLite-based cache for deduplication and history"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            cache_dir = Path(__file__).parent.parent.parent / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(cache_dir / "history.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawled_items (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                source_name TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                score REAL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_crawled_at
            ON crawled_items(crawled_at)
        """)

        conn.commit()
        conn.close()

    def _hash_url(self, url: str) -> str:
        """Generate SHA256 hash of URL"""
        return hashlib.sha256(url.encode()).hexdigest()

    def deduplicate(self, items: List[CrawledItem]) -> List[CrawledItem]:
        """Remove items that have been crawled before"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        unique_items = []
        for item in items:
            url_hash = self._hash_url(item.url)

            cursor.execute(
                "SELECT 1 FROM crawled_items WHERE url_hash = ?",
                (url_hash,)
            )

            if cursor.fetchone() is None:
                unique_items.append(item)

        conn.close()
        return unique_items

    def save_history(self, items: List[dict], score_key: str = "score"):
        """Save crawled items to history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for item in items:
            url = item.get("url", "")
            if not url:
                continue

            url_hash = self._hash_url(url)

            cursor.execute("""
                INSERT OR REPLACE INTO crawled_items
                (url_hash, url, title, source_name, crawled_at, published_at, score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                url_hash,
                url,
                item.get("title", ""),
                item.get("source_name", ""),
                datetime.now().isoformat(),
                item.get("published_at"),
                item.get(score_key)
            ))

        conn.commit()
        conn.close()

    def cleanup_old_items(self, days: int = 30):
        """Remove items older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM crawled_items
            WHERE crawled_at < datetime('now', ?)
        """, (f"-{days} days",))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted