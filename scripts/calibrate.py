"""Recalculate the operating point for the authorized five-document corpus."""

from backend.config import Settings
from backend.db import Store
from backend.index import Index
from backend.relevance import operating_point

if __name__ == "__main__":
    cfg = Settings()
    value = operating_point(Index(cfg, Store(cfg.data_dir)))
    if value is None:
        raise SystemExit("Synchronize the five official sources before calibration.")
    print("Corpus-specific threshold:", value)
