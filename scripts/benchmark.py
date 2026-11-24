"""Prepare actual FastAPI sources and record a reproducible retrieval comparison."""

import json
from pathlib import Path

from backend.config import Settings
from backend.db import Store
from backend.evaluation import run
from backend.index import Index
from backend.sources import load

if __name__ == "__main__":
    cfg = Settings()
    db = Store(cfg.data_dir)
    index = Index(cfg, db)
    for doc in load("official", cfg.data_dir):
        print(doc.doc_id, index.put(doc), flush=True)
    report = run(index)
    with db.connect() as conn:
        conn.execute("INSERT INTO evaluations(payload) VALUES (?)", (json.dumps(report),))
    Path("docs/retrieval-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report["summary"])
