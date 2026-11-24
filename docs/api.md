# API reference

Start the API and open [Swagger UI](http://127.0.0.1:8000/docs). The machine-readable schema is available at [/openapi.json](http://127.0.0.1:8000/openapi.json).

| Method | Route | Result |
|---|---|---|
| GET | /health, /ready | Process liveness and storage readiness |
| POST, GET | /v1/tickets | Create or list stored tickets |
| GET | /v1/tickets/{id} | Original ticket and current status |
| POST | /v1/tickets/{id}/analyze | Synchronous investigation and evidence |
| GET | /v1/tickets/{id}/analyses | History including edits and decisions |
| POST | /v1/tickets/{id}/review | Atomically review latest pending draft |
| POST | /v1/feedback | Save usefulness, relevance and accuracy |
| POST | /v1/search | Query with optional k, source_type and version |
| GET | /v1/documents | Published revisions and metadata |
| DELETE | /v1/documents/{id} | Admin removes source from retrieval |
| POST | /v1/ingestion/sync | Admin synchronizes official, issue or local sources |
| GET | /v1/ingestion/jobs, /v1/ingestion/jobs/{id} | Admin inspects jobs and failures |
| POST | /v1/evaluation/run | Admin benchmarks the current corpus |
| GET | /v1/evaluation/latest | Admin retrieves the latest report |

Admin requests use the X-Admin-Key header. Sync waits for completion. Inspect the returned job status and per-document detail. A partially successful sync keeps individually published sources.

```powershell
$api = 'http://127.0.0.1:8000'
$ticket = Invoke-RestMethod "$api/v1/tickets" -Method Post -ContentType application/json -Body '{"title":"Body validation","description":"A required JSON field is missing from a POST request."}'
$a = Invoke-RestMethod "$api/v1/tickets/$($ticket.id)/analyze" -Method Post
$a.citations | Select-Object title,section,url
$review = @{analysis_id=$a.id; decision='ESCALATED'; reply='Please share the redacted request and schema.'} | ConvertTo-Json
Invoke-RestMethod "$api/v1/tickets/$($ticket.id)/review" -Method Post -ContentType application/json -Body $review
```

Example health response is `{"status":"ok"}`. An invalid transition returns 409 with an error code and request ID. Missing resources return 404, malformed inputs 422, disabled admin access 403, and dependency failures 503. Client retries after a provider error are safe because the previous ticket status is restored. Creating a ticket twice creates two tickets.
