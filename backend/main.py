import hmac
import json
import logging
import sqlite3
import time
from collections import deque
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .contracts import (
    Analysis,
    Evidence,
    Feedback,
    History,
    Review,
    SavedTicket,
    Search,
    Sync,
    Ticket,
    TicketRow,
)
from .db import Store
from .generation import ChatProvider, Unavailable
from .index import Index
from .service import Desk, Problem

log = logging.getLogger("uvicorn.error")


def create_app(settings=None, encoder=None, provider=None):
    cfg = settings or Settings()
    store = Store(cfg.data_dir)
    index = Index(cfg, store, encoder)
    desk = Desk(store, index, provider or ChatProvider(cfg, index.encoder))

    @asynccontextmanager
    async def lifespan(app):
        # Single API worker owns this directory. Recover interrupted work on restart.
        with store.connect(write=True) as db:
            db.execute("""UPDATE tickets SET status=COALESCE((
                SELECT COALESCE(r.decision, 'NEEDS_REVIEW') FROM analyses a
                LEFT JOIN reviews r ON r.analysis_id=a.id
                WHERE a.ticket_id=tickets.id ORDER BY a.id DESC LIMIT 1), 'NEW')
                WHERE status='ANALYZING'""")
            db.execute("UPDATE jobs SET status='INTERRUPTED' WHERE status='RUNNING'")
        yield

    app = FastAPI(title="SupportOps AI", version="0.1.0", lifespan=lifespan)
    app.state.desk = desk
    requests = deque()

    @app.middleware("http")
    async def limits(request: Request, call_next):
        rid = uuid4().hex
        start = time.monotonic()
        while requests and start - requests[0] > 60:
            requests.popleft()
        if len(requests) >= 180:
            return JSONResponse({"error": "rate_limited", "request_id": rid}, status_code=429)
        requests.append(start)
        if request.method in ("POST", "PUT", "PATCH"):
            size = 0
            blocks = []
            async for block in request.stream():
                size += len(block)
                if size > 32768:
                    return JSONResponse({"error": "body_too_large", "request_id": rid}, status_code=413)
                blocks.append(block)
            request._body = b"".join(blocks)
        request.state.rid = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        log.info(
            json.dumps(
                {
                    "request_id": rid,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - start) * 1000, 2),
                }
            )
        )
        return response

    def error(request, status, code):
        return JSONResponse({"error": code, "request_id": request.state.rid}, status_code=status)

    @app.exception_handler(Problem)
    async def problem(request, exc):
        return error(request, exc.status, exc.code)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return error(request, 422, "invalid_input")

    @app.exception_handler(Unavailable)
    @app.exception_handler(sqlite3.Error)
    async def unavailable(request, exc):
        return error(request, 503, "dependency_unavailable")

    def admin(x_admin_key: str = Header(default="")):
        secret = cfg.admin_key.get_secret_value()
        if not secret or not hmac.compare_digest(secret.encode(), x_admin_key.encode()):
            raise Problem(403, "admin_key_required")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        try:
            store.documents()
            count = index.collection.count()
        except Exception:
            raise Unavailable() from None
        return {"storage": "ready", "indexed_chunks": count, "provider": cfg.provider}

    @app.post("/v1/tickets", status_code=201, response_model=SavedTicket)
    def create(ticket: Ticket):
        return desk.create(ticket)

    @app.get("/v1/tickets", response_model=list[TicketRow])
    def tickets():
        with store.connect() as db:
            return [
                {
                    "id": r["id"],
                    "title": json.loads(r["payload"])["title"],
                    "status": r["status"],
                    "created": r["created"],
                }
                for r in db.execute("SELECT * FROM tickets ORDER BY id DESC")
            ]

    @app.get("/v1/tickets/{ticket_id}", response_model=SavedTicket)
    def ticket(ticket_id: int):
        return desk.ticket(ticket_id)

    @app.post("/v1/tickets/{ticket_id}/analyze", response_model=Analysis)
    def analyze(ticket_id: int):
        return desk.analyze(ticket_id)

    @app.get("/v1/tickets/{ticket_id}/analyses", response_model=list[History])
    def history(ticket_id: int):
        return desk.history(ticket_id)

    @app.post("/v1/tickets/{ticket_id}/review", response_model=SavedTicket)
    def review(ticket_id: int, data: Review):
        return desk.review(ticket_id, data)

    @app.post("/v1/search", response_model=list[Evidence])
    def search(data: Search):
        try:
            return index.search(data.query, data.k, data.source_type, data.version)
        except Exception:
            raise Unavailable() from None

    @app.post("/v1/feedback", status_code=201)
    def feedback(data: Feedback):
        with store.connect(write=True) as db:
            if not db.execute(
                "SELECT 1 FROM analyses WHERE id=? AND ticket_id=?", (data.analysis_id, data.ticket_id)
            ).fetchone():
                raise Problem(404, "analysis_not_found")
            key = db.execute(
                "INSERT INTO feedback(analysis_id,payload) VALUES (?,?)",
                (data.analysis_id, data.model_dump_json()),
            ).lastrowid
        return {"id": key}

    @app.get("/v1/documents")
    def documents():
        return store.documents()

    @app.delete("/v1/documents/{doc_id}", dependencies=[Depends(admin)])
    def remove(doc_id: str):
        if not index.remove(doc_id):
            raise Problem(404, "document_not_found")
        return {"removed": doc_id}

    @app.post("/v1/ingestion/sync", dependencies=[Depends(admin)])
    def sync(data: Sync):
        return desk.sync(data)

    @app.get("/v1/ingestion/jobs", dependencies=[Depends(admin)])
    def jobs():
        with store.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 50")]

    @app.get("/v1/ingestion/jobs/{job_id}", dependencies=[Depends(admin)])
    def job(job_id: int):
        with store.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise Problem(404, "job_not_found")
            return dict(row)

    @app.get("/v1/evaluation/latest", dependencies=[Depends(admin)])
    def latest():
        with store.connect() as db:
            row = db.execute("SELECT payload FROM evaluations ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else {"status": "not_evaluated"}

    @app.post("/v1/evaluation/run", dependencies=[Depends(admin)])
    def evaluate():
        from .evaluation import run

        report = run(index)
        with store.connect() as db:
            db.execute("INSERT INTO evaluations(payload) VALUES (?)", (json.dumps(report),))
        return report

    return app
