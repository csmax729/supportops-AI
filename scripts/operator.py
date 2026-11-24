"""Run from the repository root against a running API."""

import argparse
import json
from pathlib import Path

import httpx

from backend.config import Settings

if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("action", choices=["ingest", "seed", "evaluate"])
    cli.add_argument("--url", default="http://127.0.0.1:8000")
    args = cli.parse_args()
    cfg = Settings()
    with httpx.Client(
        base_url=args.url, timeout=900, headers={"X-Admin-Key": cfg.admin_key.get_secret_value()}
    ) as client:
        if args.action == "seed":
            tickets = json.loads(Path("data/fixtures/demo.json").read_text())
            requests = [("/v1/tickets", ticket) for ticket in tickets]
        elif args.action == "ingest":
            requests = [("/v1/ingestion/sync", {"source": "official"})]
        else:
            requests = [("/v1/evaluation/run", None)]
        for url, body in requests:
            response = client.post(url, json=body)
            response.raise_for_status()
            result = response.json()
            print(json.dumps(result, indent=2))
            if result.get("status") == "FAILED":
                raise SystemExit(1)
