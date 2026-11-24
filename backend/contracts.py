from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Ticket(Contract):
    impact: Literal["unspecified", "production_outage"] = "unspecified"
    title: Short
    description: Body
    version: str = Field("", max_length=100)
    error: str = Field("", max_length=2000)
    context: str = Field("", max_length=1500)


class Search(Contract):
    query: Body
    k: int = Field(4, ge=1, le=10)
    source_type: Literal["documentation", "release", "issue", "local"] | None = None
    version: str | None = Field(None, max_length=100)


class Evidence(Contract):
    similarity: float | None = None
    doc_id: str
    chunk_id: str
    title: str
    source_type: str
    url: str
    section: str
    excerpt: str
    version: str = ""


class Finding(Contract):
    text: Body
    chunk_id: Short
    quote: Short


class Draft(Contract):
    category: Literal[
        "installation",
        "validation",
        "routing",
        "authentication",
        "database",
        "compatibility",
        "configuration",
        "performance",
        "deployment",
        "unknown",
    ]
    component: Short
    summary: Short
    sufficient: bool
    explanations: list[Finding] = Field(max_length=4)
    steps: list[Finding] = Field(max_length=6)
    missing: list[Short] = Field(max_length=6)
    escalation_reason: str = Field(max_length=500)
    reply: Body


class Review(Contract):
    analysis_id: int = Field(gt=0)
    decision: Literal["APPROVED", "REJECTED", "ESCALATED"]
    reply: Body


class Feedback(Contract):
    ticket_id: int
    analysis_id: int
    useful: bool
    relevant: bool
    accurate: bool
    comments: str = Field("", max_length=1500)


class Sync(Contract):
    source: Literal["official", "local", "issue"] = "official"
    issue_number: int | None = Field(None, ge=1)


class SavedTicket(Ticket):
    id: int
    status: str
    created: str


class TicketRow(Contract):
    id: int
    title: str
    status: str
    created: str


class Analysis(Contract):
    id: int
    ticket_id: int
    draft: Draft
    provider: str | None
    priority: str
    escalation: bool
    citations: list[Evidence]
    retrieved: list[Evidence]
    usage: dict
    retrieval_ms: float
    generation_ms: float
    total_ms: float


class History(Analysis):
    created: str
    edited_reply: str | None
    decision: str | None
