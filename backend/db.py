import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


def now():
    return datetime.now(UTC).isoformat()


class Store:
    """Short-lived transactions; WAL readers can inspect history during inference."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "supportops.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tickets(
                    id INTEGER PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL,
                    created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS analyses(
                    id INTEGER PRIMARY KEY, ticket_id INTEGER REFERENCES tickets, payload TEXT NOT NULL,
                    created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews(
                    id INTEGER PRIMARY KEY, analysis_id INTEGER UNIQUE REFERENCES analyses,
                    decision TEXT NOT NULL, reply TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS feedback(
                    id INTEGER PRIMARY KEY, analysis_id INTEGER REFERENCES analyses, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents(
                    id TEXT PRIMARY KEY, revision TEXT NOT NULL, metadata TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(
                    id INTEGER PRIMARY KEY, status TEXT NOT NULL, detail TEXT, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evaluations(
                    id INTEGER PRIMARY KEY, payload TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self, *, write=False):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        finally:
            db.close()

    def documents(self):
        with self.connect() as db:
            return [
                dict(id=r["id"], revision=r["revision"], updated=r["updated"], **json.loads(r["metadata"]))
                for r in db.execute("SELECT * FROM documents ORDER BY id")
            ]
