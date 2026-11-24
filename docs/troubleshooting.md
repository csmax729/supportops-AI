# Troubleshooting

| Symptom | Inspect | Recovery |
|---|---|---|
| Knowledge base empty | Latest sync job detail | Verify model download and source connectivity. Retry sync. |
| Admin receives 403 | ADMIN_KEY in the API environment | Paste that local value in the admin form. Restart the API after editing .env. |
| First query is slow | Cold model cache, CPU threads | Prime the encoder with python -m scripts.cache_model. Keep the data directory persistent. |
| Index config mismatch | Embedding model identity and revision | Select a fresh DATA_DIR and sync. Retain the original for rollback. |
| Analysis returns 503 | /ready, chat daemon, selected model, credentials | Pull the configured model or repair the hosted key. Retry the ticket after service recovery. |
| Review returns 409 | Latest analysis ID and status | Refresh Investigations and review the current pending draft. |
| Model quotes cannot be verified | Retrieved excerpts and version context | Escalate or ask for missing details. A larger model may follow the contract more reliably. |
| UI cannot reach API | API_URL in the Streamlit process | Use loopback locally and the api service name inside Compose. |
| PDF yields no content | PDF text layer | Use an authorized text export. OCR is outside this version. |

A Windows Hugging Face warning about cache symlinks is compatible with inference but may increase disk usage. Keep generated models outside Git. Before deleting data, make a copy of the entire stopped runtime directory.
