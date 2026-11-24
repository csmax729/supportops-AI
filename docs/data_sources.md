# Sources and reuse

Official sync reads the main article from FastAPI’s [request bodies](https://fastapi.tiangolo.com/tutorial/body/), [path parameters](https://fastapi.tiangolo.com/tutorial/path-params/), [exceptions](https://fastapi.tiangolo.com/tutorial/handling-errors/), [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) and [release notes](https://fastapi.tiangolo.com/release-notes/). Release sync retains the newest five version sections when machine-readable headings are present. Each row retains its canonical upstream URL. Runtime snapshots are excluded from the distribution. The FastAPI repository publishes its [MIT license](https://github.com/fastapi/fastapi/blob/master/LICENSE).

GitHub sync takes an operator-selected issue number. It reads number, state and modification date from the official repository endpoint. It discards comments, title, body, author and pull requests. Issue state alone cannot support a recommendation. This limits the value of historical issue similarity until a rights-cleared corpus is available. [GitHub Issues API](https://docs.github.com/en/rest/issues/issues#get-an-issue)

The local inbox accepts operator-authorized Markdown, plain text and text-bearing PDF. Each PDF page becomes a section. Delete retired documents from the knowledge-base screen, including files removed from the inbox. Local files have no public citation URL. Only place material suitable for every user of the desk in the inbox.

For a rights-cleared issue excerpt, the operator may place a JSON record in `runtime/issue-excerpts/<issue_number>.json` with nonempty `permission`, `attribution` and `excerpt` strings. Issue sync combines only the reviewed excerpt with current official metadata. Record the actual reuse permission and redact identifying details before importing.

To assign a version to a local historical guide, begin its text with a line such as `Version: 0.70.0`. Local sync copies that value into source and chunk metadata. A search with `{"query":"request schema","version":"0.70.0"}` then limits retrieval to documents tagged with that exact version.

Project-authored ticket fixtures and evaluation cases are synthetic and covered by the project license. The pinned English MiniLM encoder produces normalized embeddings locally and is published under Apache-2.0. Long inputs exceed its 256 word-piece limit, which motivated smaller default chunks. [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
