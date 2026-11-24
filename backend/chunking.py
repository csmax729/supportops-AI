import hashlib
import re
from dataclasses import dataclass


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    source_type: str
    url: str
    text: str
    version: str = ""


def sections(text, title):
    lines = []
    heading = title
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match[1][0]
            fence = None if fence == marker else fence or marker
        if not fence and re.match(r"^#{1,6}\s", line):
            if lines:
                yield heading, "\n".join(lines)
            heading, lines = line.lstrip("# ").strip(), []
        else:
            lines.append(line)
    if lines:
        yield heading, "\n".join(lines)


def chunks(doc, size=130, overlap=24):
    if not 0 <= overlap < size:
        raise ValueError("Overlap must be smaller than chunk size")
    for heading, body in sections(doc.text, doc.title):
        tokens = list(re.finditer(r"\S+", body))
        start = 0
        while start < len(tokens):
            end = min(start + size, len(tokens))
            yield heading, body[tokens[start].start() : tokens[end - 1].end()]
            if end == len(tokens):
                break
            start = end - overlap
