import json
import time
from threading import Lock

from .contracts import Ticket
from .db import now
from .generation import Unavailable, abstain, verify
from .relevance import operating_point
from .sources import load


class Problem(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


class Desk:
    def __init__(self, store, index, provider):
        self.store, self.index, self.provider = store, index, provider
        self.sync_lock = Lock()

    def create(self, ticket):
        with self.store.connect() as db:
            key = db.execute(
                "INSERT INTO tickets(payload,status,created) VALUES (?,'NEW',?)",
                (ticket.model_dump_json(), now()),
            ).lastrowid
        return self.ticket(key)

    def ticket(self, key):
        with self.store.connect() as db:
            r = db.execute("SELECT * FROM tickets WHERE id=?", (key,)).fetchone()
        if not r:
            raise Problem(404, "ticket_not_found")
        return dict(id=key, status=r["status"], created=r["created"], **json.loads(r["payload"]))

    def history(self, key):
        self.ticket(key)
        with self.store.connect() as db:
            rows = db.execute(
                """SELECT a.*, r.reply AS edited_reply,r.decision FROM analyses a
                LEFT JOIN reviews r ON r.analysis_id=a.id WHERE ticket_id=? ORDER BY a.id DESC""",
                (key,),
            )
            return [
                dict(
                    id=r["id"],
                    ticket_id=key,
                    created=r["created"],
                    edited_reply=r["edited_reply"],
                    decision=r["decision"],
                    **json.loads(r["payload"]),
                )
                for r in rows
            ]

    def analyze(self, key):
        original = self.ticket(key)
        previous = original["status"]
        if previous not in ("NEW", "NEEDS_REVIEW", "REJECTED", "ESCALATED"):
            raise Problem(409, "analysis_transition_invalid")
        with self.store.connect(write=True) as db:
            if not db.execute(
                "UPDATE tickets SET status='ANALYZING' WHERE id=? AND status=?", (key, previous)
            ).rowcount:
                raise Problem(409, "ticket_changed")
        started = time.perf_counter()
        try:
            ticket = Ticket(**{k: original[k] for k in Ticket.model_fields if k in original})
            query = "\n".join(v for v in ticket.model_dump(exclude={"impact"}).values() if v)
            try:
                evidence = self.index.search(query[:4000])
                cutoff = operating_point(self.index) if evidence else None
            except Exception:
                raise Unavailable("Knowledge index unavailable") from None
            retrieved = time.perf_counter()
            usage = {}
            called_model = False
            if evidence and cutoff is not None and evidence[0].similarity < cutoff:
                draft = abstain(
                    "The nearest source fell below the relevance cutoff calibrated for this corpus."
                )
            elif evidence:
                called_model = True
                draft, usage = self.provider.generate(ticket, evidence)
                draft = verify(draft, evidence)
            else:
                draft = abstain("No indexed evidence was available for this investigation.")
            finished = time.perf_counter()
            refs = {x.chunk_id for x in draft.steps + draft.explanations}
            result = {
                "draft": draft.model_dump(),
                "provider": self.provider.name if called_model else None,
                "priority": "high" if ticket.impact == "production_outage" else "normal",
                "escalation": not draft.sufficient or bool(draft.escalation_reason),
                "citations": [e.model_dump() for e in evidence if e.chunk_id in refs],
                "retrieved": [e.model_dump() for e in evidence],
                "usage": usage,
                "retrieval_ms": round(1000 * (retrieved - started), 2),
                "generation_ms": round(1000 * (finished - retrieved), 2),
                "total_ms": round(1000 * (finished - started), 2),
            }
            with self.store.connect(write=True) as db:
                cur = db.execute(
                    "INSERT INTO analyses(ticket_id,payload,created) VALUES (?,?,?)",
                    (key, json.dumps(result), now()),
                )
                db.execute("UPDATE tickets SET status='NEEDS_REVIEW' WHERE id=?", (key,))
                return dict(id=cur.lastrowid, ticket_id=key, **result)
        except Exception:
            with self.store.connect(write=True) as db:
                db.execute("UPDATE tickets SET status=? WHERE id=? AND status='ANALYZING'", (previous, key))
            raise

    def review(self, key, decision):
        self.ticket(key)
        with self.store.connect(write=True) as db:
            last = db.execute("SELECT max(id) FROM analyses WHERE ticket_id=?", (key,)).fetchone()[0]
            if (
                last != decision.analysis_id
                or not db.execute(
                    "UPDATE tickets SET status=? WHERE id=? AND status='NEEDS_REVIEW'",
                    (decision.decision, key),
                ).rowcount
            ):
                raise Problem(409, "review_requires_latest_pending_analysis")
            db.execute(
                "INSERT INTO reviews(analysis_id,decision,reply,created) VALUES (?,?,?,?)",
                (last, decision.decision, decision.reply, now()),
            )
        return self.ticket(key)

    def sync(self, request):
        if not self.sync_lock.acquire(False):
            raise Problem(409, "sync_in_progress")
        try:
            with self.store.connect() as db:
                job = db.execute("INSERT INTO jobs(status,created) VALUES ('RUNNING',?)", (now(),)).lastrowid
            detail = {}
            try:
                for doc in load(request.source, self.index.settings.data_dir, request.issue_number):
                    detail[doc.doc_id] = self.index.put(doc)
                status = "COMPLETE"
            except Exception as exc:
                detail["failure"] = type(exc).__name__
                status = "FAILED"
            with self.store.connect() as db:
                db.execute("UPDATE jobs SET status=?, detail=? WHERE id=?", (status, json.dumps(detail), job))
            return {"id": job, "status": status, "detail": detail}
        finally:
            self.sync_lock.release()
