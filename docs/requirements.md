# Requirements and acceptance record

The primary user is a technical support engineer investigating a SaaS API ticket. The administrator maintains a small authorized knowledge base and runs evaluations. A recommendation always goes through a human decision before it can be used as an approved response.

| Milestone | Implemented behavior | Verification |
|---|---|---|
| Requirements and design | Local modular monolith, two operating roles, ticket/review contracts and source provenance | Architecture diagrams, API reference and design notes are included |
| Environment | Python 3.11, uv transitive lock, generated local administrator credential | Installed in a new project environment on Windows |
| Ingestion | Article extraction, metadata-only GitHub lookup, optional rights-cleared excerpts, local Markdown/text/PDF, chunking and revision publication | Five official articles indexed, synthetic local document ingested twice without duplication |
| Retrieval | Cached MiniLM encoder, normalized vectors, persistent Chroma, bounded results and source snapshots | Actual 384-dimensional CPU embeddings and reopened index; retrieval report records corpus revisions |
| Model integration | Hosted chat, Ollama and llama.cpp adapters, Pydantic contract, abstention and quote validation | Local real-model evidence in the evaluation reports; hosted and Ollama live inference remain unverified |
| API and review | Ticket creation, investigation, analysis history, edited approval/rejection/escalation and feedback | FastAPI TestClient exercises production routes, invalid input, stale reviews, admin denial and dependency failure |
| Frontend | Dashboard, ticket entry, investigation history, knowledge-base operations and evaluation | Live Streamlit overview rendered against the API and captured in overview.png |
| End-to-end validation | Synthetic tickets exercise actual retrieval, generation and persisted review | See the live results and their interpretation in evaluation.md |
| Evaluation | Separate reference labels and synthetic behavioral cases, per-query rankings, latency, citation membership and reviewer feedback | Actual retrieval comparison and live-provider checks; independent human quality judgments pending |
| Advanced retrieval | Compare document-diverse selection against dense ranking | Tied on all eight labeled queries. Dense remains the default |
| Reliability | Single-writer index publication, model identity checks, request limits, bounded retries, safe errors and interrupted-work recovery | Offline suite includes failed updates, incompatible encoders, request size, timeout, missing credentials, injection containment and rollback |
| Deployment | Separate API and UI images, locked dependencies, persistent API volume, service DNS and loopback ports | Built both Linux images on Windows Docker Desktop. Compose started both services. The API reported storage ready on a new empty volume and Streamlit returned a healthy response. |
| Documentation | Reproducible setup, diagrams, API examples, demo script, limitations and source policy | Release ZIP checked for broken local Markdown links and unexpected generated files |

## Scope and remaining work

The release passed 18 automated tests on Windows with Python 3.11.7. The suite includes an engineer editing and approving a draft through Streamlit, historical version metadata, and recovery after an interrupted reanalysis. All five UI views rendered against the running API. The local CPU provider was exercised on two full investigations and five controlled generation cases. [Measured results and observed failures](evaluation.md)

- Ticket states cover NEW, ANALYZING, NEEDS_REVIEW, APPROVED, REJECTED and ESCALATED. Closing customer tickets in an external system is outside this application.
- Knowledge sync is synchronous with per-source status. Retired sources can be removed by an administrator. Durable distributed queues, background crawling, OCR and tenant-specific retrieval are deferred.
- Text length and output limits bound prompt size approximately. Tokenizer-accurate budgets, calibrated corpus-specific relevance thresholds and historical version coverage need further evaluation.
- The code supports metadata filters for known versions. Current upstream tutorial pages generally describe the current release. Exact-version investigations require matching source evidence.
- Public hosting, hosted-provider billing, production traffic, live Ollama and cross-platform container execution have no deployment claim here.
- Extend the small evaluation set with independently labeled real tickets, adversarial documents, and blinded human assessments before estimating answer reliability or business impact.

For startup and validation commands see the [README](../README.md). For operational constraints see the [security notes](security.md) and [deployment guide](deployment.md).
