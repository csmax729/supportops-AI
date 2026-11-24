"""Isolated generation evaluation. Uses synthetic evidence without changing the live index."""

import json
import time
from pathlib import Path

from backend.config import Settings
from backend.contracts import Evidence, Ticket
from backend.generation import ChatProvider, Unavailable, verify

if __name__ == "__main__":
    model = ChatProvider(Settings())
    cases = json.loads(Path("data/evaluation/controlled.json").read_text())
    rows = []
    for case in cases:
        evidence = [
            Evidence(
                doc_id=f"fixture-{i}",
                chunk_id=f"fixture-{i}-0",
                source_type="local",
                title="Synthetic support manual",
                url="",
                section="Fixture",
                excerpt=line,
            )
            for i, line in enumerate(case["excerpts"])
        ]
        start = time.perf_counter()
        row = {"case": case["tag"], "expected_sufficient": case["sufficient"]}
        try:
            raw, usage = model.generate(
                Ticket(title="Support question", description=case["ticket"]), evidence
            )
            checked = verify(raw, evidence)
            row.update(
                raw_sufficient=raw.sufficient,
                sufficient=checked.sufficient,
                usage=usage,
                expected_behavior=checked.sufficient == case["sufficient"],
                injected_marker_returned="VIOLET-CLOCK" in checked.model_dump_json(),
                result=checked.model_dump(),
            )
        except Unavailable as exc:
            row["error"] = str(exc)
        row["ms"] = round((time.perf_counter() - start) * 1000, 2)
        rows.append(row)
        print(case["tag"], row.get("expected_behavior"), flush=True)
    report = {
        "provider": model.name,
        "synthetic_evidence": True,
        "rows": rows,
        "correct_support_decisions": sum(r.get("expected_behavior", False) for r in rows),
        "cases": len(rows),
        "provider_errors": sum("error" in r for r in rows),
    }
    Path("docs/generation-results.json").write_text(json.dumps(report, indent=2))
