import json
import math
import statistics
import time
from pathlib import Path

from .db import now

DATA = Path(__file__).resolve().parents[1] / "data" / "evaluation"


def scores(ids, labels, k):
    hits = set(ids[:k]) & set(labels)
    rank = next((i for i, d in enumerate(ids[:k], 1) if d in labels), None)
    return {"recall": len(hits) / len(labels), "precision": len(hits) / k, "rr": 1 / rank if rank else 0}


def investigation_metrics(store):
    with store.connect() as db:
        analyses = [json.loads(r[0]) for r in db.execute("SELECT payload FROM analyses")]
        feedback = [json.loads(r[0]) for r in db.execute("SELECT payload FROM feedback")]
    timings = sorted(a["total_ms"] for a in analyses)
    citations = 0
    verified = 0
    for analysis in analyses:
        evidence = {e["chunk_id"]: e["excerpt"] for e in analysis["retrieved"]}
        for claim in analysis["draft"]["steps"] + analysis["draft"]["explanations"]:
            citations += 1
            verified += claim["quote"] in evidence.get(claim["chunk_id"], "")
    return {
        "completed_analyses": len(analyses),
        "abstentions": sum(not a["draft"]["sufficient"] for a in analyses),
        "cited_claims": citations,
        "verified_quote_fraction": verified / citations if citations else None,
        "latency_p50_ms": statistics.median(timings) if timings else None,
        "latency_p95_ms": timings[math.ceil(0.95 * len(timings)) - 1] if len(timings) >= 20 else None,
        "feedback_submissions": len(feedback),
        "reviewer_ratings": {
            key: sum(row[key] for row in feedback) / len(feedback) if feedback else None
            for key in ("accurate", "relevant", "useful")
        },
    }


def run(index, k=3):
    """Compare chunk-ranked retrieval against document diversity on identical labeled queries."""
    cases = json.loads((DATA / "heldout.json").read_text())
    rows = []
    inventory = index.store.documents()
    for query, labels in cases:
        start = time.perf_counter()
        try:
            retrieved = index.search(query, 3 * k)
            ids = [r.doc_id for r in retrieved]
            rows.append(
                {
                    "query": query,
                    "expected": labels,
                    "retrieved": ids,
                    "dense": scores(ids, labels, k),
                    "diverse": scores(list(dict.fromkeys(ids)), labels, k),
                    "ms": round(1000 * (time.perf_counter() - start), 2),
                }
            )
        except Exception as exc:
            rows.append({"query": query, "expected": labels, "error": type(exc).__name__})
    good = [r for r in rows if "ms" in r]
    summary = {
        method: {
            metric: sum(r[method][metric] for r in good) / len(rows)
            for metric in ("recall", "precision", "rr")
        }
        for method in ("dense", "diverse")
    }
    latency = sorted(r["ms"] for r in good)
    return {
        "status": "evaluated",
        "created": now(),
        "encoder": index.encoder.identity,
        "k": k,
        "cases": len(rows),
        "errors": len(rows) - len(good),
        "corpus": {d["id"]: d["revision"] for d in inventory},
        "summary": summary,
        "investigations": investigation_metrics(index.store),
        "latency_p50_ms": statistics.median(latency) if latency else None,
        "latency_p95_ms": latency[math.ceil(0.95 * len(latency)) - 1] if len(latency) >= 20 else None,
        "rows": rows,
    }
