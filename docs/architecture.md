# Architecture

```mermaid
flowchart LR
    UI[Streamlit] --> API[FastAPI]
    API --> Desk[Ticket service]
    API --> Sync[Source sync]
    Sync --> Encoder[MiniLM on CPU]
    Encoder --> Chroma[(Chroma)]
    Desk --> Chroma
    Desk --> Prompt[LangChain chat template]
    Prompt --> Model[Chat provider]
    Model --> Validator[Pydantic and citation checks]
    Validator --> SQL[(SQLite WAL)]
    Sync --> SQL
    API --> SQL
```

```mermaid
sequenceDiagram
    actor Engineer
    Engineer->>API: Create ticket
    API->>DB: Save NEW
    Engineer->>API: Analyze
    API->>DB: Claim ticket
    API->>Chroma: Search published revisions
    Chroma-->>API: Evidence and provenance
    API->>LLM: Bounded evidence and JSON contract
    LLM-->>API: Proposed findings
    API->>API: Validate schema, IDs and quotes
    API->>DB: Save analysis and mark NEEDS_REVIEW
    Engineer->>API: Edit and review latest analysis
    API->>DB: Atomically persist decision and edited reply
```

```mermaid
flowchart TD
    Pages[Allowed pages or operator inbox] --> Parse[Extract article sections]
    Parse --> Hash[Hash content and chunk configuration]
    Hash --> Embed[Embed a complete candidate revision]
    Embed --> Upsert[Write versioned chunks]
    Upsert --> Publish[Commit active revision to SQLite]
    Publish --> Cleanup[Delete older chunks]
```

```mermaid
flowchart LR
    Browser --> UI[Streamlit container 8501]
    UI --> API[API container 8000]
    API --> Volume[Persistent volume]
    API --> Chat[Host Ollama or hosted API]
    API --> Source[Upstream source servers]
```

One process owns the index directory. SQLite reserves a ticket before inference and releases its write lock during model I/O. A concurrent review or analysis must win the expected-state update. The latest analysis ID prevents stale review submissions. The accepted edit and status change share a transaction. On startup, interrupted claims and ingestion jobs recover from persisted history. Index writes stage new chunks under their content revision. Retrieval filters against committed revision identifiers.
