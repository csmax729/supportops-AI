"""Exercise a running API using synthetic input and the configured real provider."""

import json
import os
from pathlib import Path

import httpx

if __name__ == "__main__":
    with httpx.Client(base_url=os.getenv("API_URL", "http://127.0.0.1:8000"), timeout=600) as client:

        def request(method, path, data=None):
            response = client.request(method, path, json=data)
            response.raise_for_status()
            return response.json()

        samples = json.loads(Path("data/fixtures/demo.json").read_text())
        samples = [
            samples[0],
            {"title": "[Synthetic] Gardening", "description": "Which soil should I buy for mint?"},
        ]
        rows = []
        for sample in samples:
            ticket = request("POST", "/v1/tickets", sample)
            path = f"/v1/tickets/{ticket['id']}"
            result = request("POST", path + "/analyze")
            draft = result["draft"]
            retrieved = {e["chunk_id"]: e["excerpt"] for e in result["retrieved"]}
            verified = all(
                f["quote"] in retrieved[f["chunk_id"]] for f in draft["steps"] + draft["explanations"]
            )
            decision = "ESCALATED" if result["escalation"] else "APPROVED"
            request(
                "POST",
                path + "/review",
                {
                    "analysis_id": result["id"],
                    "decision": decision,
                    "reply": "Synthetic workflow check. " + draft["reply"],
                },
            )
            history = request("GET", path + "/analyses")[0]
            rows.append(
                {
                    "title": ticket["title"],
                    "provider": result["provider"],
                    "sufficient": draft["sufficient"],
                    "citations": len(result["citations"]),
                    "source_titles": [e["title"] for e in result["citations"]],
                    "reply": draft["reply"],
                    "findings": draft["steps"],
                    "review_decision": history["decision"],
                    "quotes_verified": verified,
                    "review_persisted": history["decision"] == decision,
                    "escalation_reason": draft["escalation_reason"],
                    "latency_ms": result["total_ms"],
                    "usage": result["usage"],
                }
            )
            print(rows[-1], flush=True)
        Path("docs/live-results.json").write_text(json.dumps(rows, indent=2))
        if not (
            rows[0]["citations"]
            and rows[0]["sufficient"]
            and not rows[1]["sufficient"]
            and all(r["quotes_verified"] and r["review_persisted"] for r in rows)
        ):
            raise SystemExit("Inspect live behavior: at least one acceptance condition failed.")
