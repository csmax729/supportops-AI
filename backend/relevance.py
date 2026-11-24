"""Corpus-specific abstention operating point for the official FastAPI sources."""

import json
from pathlib import Path

CASES = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "calibration.json"
OFFICIAL = {"body", "errors", "paths", "releases", "dependencies"}


def fit(index, revisions):
    cases = json.loads(CASES.read_text())
    rows = [{"query": q, "relevant": label, "score": index.search(q, 1)[0].similarity} for q, label in cases]
    scores = sorted({r["score"] for r in rows})
    if len(scores) < 2:
        return None
    thresholds = [(a + b) / 2 for a, b in zip(scores, scores[1:], strict=False)]

    def correct(t):
        return sum((r["score"] >= t) == r["relevant"] for r in rows)

    threshold = max(thresholds, key=lambda t: (correct(t), t))
    return {
        "model": index.encoder.identity,
        "revisions": revisions,
        "threshold": threshold,
        "correct_development_labels": correct(threshold),
        "rows": rows,
    }


def operating_point(index):
    with index.lock:
        revisions = {d["id"]: d["revision"] for d in index.store.documents()}
        if set(revisions) != OFFICIAL:
            return None
        path = index.settings.data_dir / "calibration.json"
        if path.is_file():
            report = json.loads(path.read_text())
            if report["model"] == index.encoder.identity and report["revisions"] == revisions:
                return report["threshold"]
        report = fit(index, revisions)
        if report:
            staged = path.with_suffix(".tmp")
            staged.write_text(json.dumps(report, indent=2))
            staged.replace(path)
            return report["threshold"]
        return None
