"""Fixed upstream routes and an operator-owned inbox. No user-supplied network URLs."""

import re
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify
from pypdf import PdfReader

from .chunking import Document

PAGES = {
    "body": ("Request body", "tutorial/body/", "documentation"),
    "errors": ("Handling errors", "tutorial/handling-errors/", "documentation"),
    "paths": ("Path parameters", "tutorial/path-params/", "documentation"),
    "dependencies": ("Dependencies", "tutorial/dependencies/", "documentation"),
    "releases": ("Release notes", "release-notes/", "release"),
}


def fetch(url):
    for attempt in range(3):
        try:
            with httpx.stream("GET", url, timeout=20, follow_redirects=False) as response:
                if response.status_code in (403, 429) and "retry-after" in response.headers:
                    delay = response.headers["retry-after"]
                    if not delay.isdigit() or int(delay) > 8:
                        response.raise_for_status()
                    time.sleep(int(delay))
                response.raise_for_status()
                data = bytearray()
                for part in response.iter_bytes():
                    data.extend(part)
                    if len(data) > 12_000_000:
                        raise ValueError("Source exceeds size limit")
                return bytes(data)
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in (
                429,
                502,
                503,
                504,
            ):
                raise
            if attempt == 2 or (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.headers.get("retry-after", "0") not in map(str, range(9))
            ):
                raise
            time.sleep(2**attempt)


def clean_html(raw):
    soup = BeautifulSoup(raw, "html.parser")
    article = soup.select_one("article") or soup.select_one("main")
    if not article:
        raise ValueError("Article body missing")
    for node in article.select("nav, script, style, .headerlink, .md-content__button"):
        node.decompose()
    return markdownify(str(article), heading_style="ATX").strip()


def load(source, directory: Path, issue_number=None):
    if source == "official":
        for key, (title, path, kind) in PAGES.items():
            url = "https://fastapi.tiangolo.com/" + path
            body = clean_html(fetch(url))
            if key == "releases":
                headings = list(re.finditer(r"(?m)^##\s+\d+\.\d+\.\d+", body))
                if len(headings) > 5:
                    body = body[: headings[5].start()]
            yield Document(key, title, kind, url, body)
    elif source == "issue":
        import json

        if not issue_number:
            raise ValueError("Select an issue number")
        issue = json.loads(fetch(f"https://api.github.com/repos/fastapi/fastapi/issues/{issue_number}"))
        if "pull_request" in issue:
            raise ValueError("Select an issue, not a pull request")
        title = f"FastAPI issue #{issue_number}"
        # Metadata only. No author handles, comments or community-authored prose.
        body = f"{title}\nState: {issue['state']}\nUpdated: {issue['updated_at']}"
        # Optional rights-cleared excerpt supplied by an operator, tied to this issue.
        excerpt_path = directory / "issue-excerpts" / f"{issue_number}.json"
        if excerpt_path.is_file() and not excerpt_path.is_symlink():
            if excerpt_path.stat().st_size > 32000:
                raise ValueError("Issue excerpt exceeds the size limit")
            record = json.loads(excerpt_path.read_text(encoding="utf-8-sig"))
            if not all(
                isinstance(record.get(k), str) and record[k].strip()
                for k in ("permission", "attribution", "excerpt")
            ):
                raise ValueError("Record permission and attribution for the reviewed excerpt")
            body += f"\nRights: {record['permission']}\nAttribution: {record['attribution']}\n\n{record['excerpt']}"
        yield Document(
            f"issue-{issue_number}",
            title,
            "issue",
            f"https://github.com/fastapi/fastapi/issues/{issue_number}",
            body,
        )
    else:
        inbox = directory / "inbox"
        inbox.mkdir(exist_ok=True)
        for path in sorted(inbox.iterdir()):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            if path.suffix.lower() == ".pdf":
                reader = PdfReader(path)
                body = "\n".join(
                    f"## Page {i}\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages, 1)
                )
            elif path.suffix.lower() in {".md", ".txt"}:
                body = path.read_text(encoding="utf-8-sig")
            else:
                continue
            # An explicit first-line version is useful for operator-maintained historical guides.
            tag = re.match(r"\AVersion:[ \t]*([\w.+-]{1,100})[ \t]*(?:\r?\n|$)", body, re.I)
            yield Document("local-" + path.name, path.stem, "local", "", body, tag[1] if tag else "")
