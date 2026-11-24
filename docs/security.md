# Operating boundary

Run as a trusted local support desk. Loopback port mappings and same-origin browser defaults restrict network exposure. Ticket reads and review actions assume one trusted operator. Administrative routes require a constant-time checked X-Admin-Key and deny access when the configured secret is empty. Public hosting requires identity, per-ticket authorization, HTTPS and per-user quotas at a gateway.

Only predefined HTTPS source routes are fetched. Redirects are disabled. Operators select a numeric issue ID or place licensed documents in a private inbox. File and response sizes, retry counts, chat duration and ingestion concurrency are bounded. Keep PDFs from untrusted third parties outside this process. PDF extraction lacks an isolated parser and CPU quota.

The API limits incoming JSON to 32 KiB and 180 requests per minute across the process. It writes request IDs, status and timing to logs. SQLite retains the original ticket, edits and retrieved evidence in plaintext. The provider receives a bounded copy with heuristic masking of common secrets and email addresses. Redact sensitive data before entering tickets. The masking expression cannot recognize every credential or identifier.

Retrieved content is quoted as data, with the system message defining allowed behavior. No tools or command executor are available to the model. Valid quotations can still be irrelevant or misleading. Verify actions, version compatibility and customer impact before approving. The project includes no tenant isolation, SSO, retention scheduler or enterprise security certification.
