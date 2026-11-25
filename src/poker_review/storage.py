"""Local persistence. Parameterized SQL; no credentials in stored reports."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi.encoders import jsonable_encoder


def encode(value) -> str:
    # Preserve Decimal exactly, including through API/storage round trips.
    from decimal import Decimal
    return json.dumps(jsonable_encoder(value, custom_encoder={Decimal: str}), ensure_ascii=False)


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS hands (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, report TEXT NOT NULL,
                    review TEXT, is_demo INTEGER NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, content_hash TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
                    tags TEXT NOT NULL, source TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS vectors (
                    cache_key TEXT PRIMARY KEY, vector TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def save_hand(self, hand, report, is_demo=False):
        payload = hand.model_dump(mode="json")
        canonical = {key: value for key, value in payload.items() if key != "hand_id"}
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            duplicate = db.execute("SELECT id FROM hands WHERE content_hash=? AND id!=?", (digest, hand.hand_id)).fetchone()
            if duplicate:
                raise ValueError(f"相同牌局已儲存為 {duplicate['id']}；不重複計入統計。")
            db.execute("""INSERT INTO hands VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, report=excluded.report,
                review=NULL, is_demo=excluded.is_demo, updated_at=excluded.updated_at,
                content_hash=excluded.content_hash""",
                (hand.hand_id, encode(payload), encode(report), int(is_demo), now, now, digest))
        return self.hand(hand.hand_id)

    def hand(self, hand_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM hands WHERE id=?", (hand_id,)).fetchone()
        return self._decode(row) if row else None

    def hands(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM hands ORDER BY updated_at DESC").fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row):
        result = dict(row)
        for key in ("payload", "report", "review"):
            result[key] = json.loads(result[key]) if result[key] else None
        result["is_demo"] = bool(result["is_demo"])
        result.pop("content_hash")
        return result

    def save_review(self, hand_id, review, expected_updated_at):
        with self.connect() as db:
            changed = db.execute("UPDATE hands SET review=? WHERE id=? AND updated_at=?",
                                 (encode(review), hand_id, expected_updated_at)).rowcount
            if changed != 1:
                raise ValueError("牌局已更新或刪除；這份復盤未儲存，請重新分析。")

    def delete_hand(self, hand_id):
        with self.connect() as db:
            return db.execute("DELETE FROM hands WHERE id=?", (hand_id,)).rowcount > 0

    def notes(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM notes ORDER BY title").fetchall()
        return [{**dict(row), "tags": json.loads(row["tags"])} for row in rows]

    def save_note(self, note):
        with self.connect() as db:
            db.execute("INSERT INTO notes VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET title=excluded.title, body=excluded.body, tags=excluded.tags, source=excluded.source",
                       (note["id"], note["title"], note["body"], encode(note["tags"]), note["source"]))

    def vector(self, key):
        with self.connect() as db:
            row = db.execute("SELECT vector FROM vectors WHERE cache_key=?", (key,)).fetchone()
        return json.loads(row["vector"]) if row else None

    def save_vector(self, key, vector):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO vectors VALUES (?, ?)", (key, encode(vector)))
