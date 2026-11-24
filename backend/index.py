import json
from functools import cached_property
from threading import RLock

from .chunking import chunks, digest
from .contracts import Evidence


class Encoder:
    def __init__(self, settings):
        self.settings = settings
        self.identity = f"{settings.embedding_model}@{settings.embedding_revision}:normalized-v1"

    @cached_property
    def model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(
            self.settings.embedding_model,
            revision=self.settings.embedding_revision,
            device="cpu",
            cache_folder=str(self.settings.data_dir / "models"),
        )

    def encode(self, texts):
        if not texts:
            return []
        return self.model.encode(
            texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False
        ).tolist()


class Index:
    def __init__(self, settings, store, encoder=None):
        self.settings, self.store = settings, store
        self.encoder = encoder or Encoder(settings)
        self.lock = RLock()

    @cached_property
    def collection(self):
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=str(self.settings.data_dir / "chroma"), settings=Settings(anonymized_telemetry=False)
        )
        col = client.get_or_create_collection(
            "supportops",
            embedding_function=None,
            metadata={"encoder": self.encoder.identity, "hnsw:space": "cosine"},
        )
        if col.metadata.get("encoder") != self.encoder.identity:
            raise ValueError("Embedding configuration differs. Select a new data directory.")
        return col

    def put(self, doc):
        from .db import now

        settings = self.settings
        meta = {"title": doc.title, "url": doc.url, "source_type": doc.source_type, "version": doc.version}
        rev = digest(json.dumps([doc.doc_id, doc.text, meta, settings.chunk_words, settings.overlap_words]))
        with self.lock:
            col = self.collection
            with self.store.connect() as db:
                old = db.execute("SELECT revision FROM documents WHERE id=?", (doc.doc_id,)).fetchone()
            if old and old[0] == rev:
                return "unchanged"
            entries = list(chunks(doc, settings.chunk_words, settings.overlap_words))
            if not entries:
                raise ValueError("Empty document")
            for offset in range(0, len(entries), 64):
                batch = entries[offset : offset + 64]
                texts = [body for _, body in batch]
                col.upsert(
                    ids=[f"{rev}-{offset + i}" for i in range(len(batch))],
                    documents=texts,
                    embeddings=self.encoder.encode([f"{doc.title}\n{h}\n{t}" for h, t in batch]),
                    metadatas=[dict(**meta, doc_id=doc.doc_id, revision=rev, section=h) for h, _ in batch],
                )
            # Only fully written revisions are visible to readers.
            with self.store.connect(write=True) as db:
                db.execute(
                    "INSERT OR REPLACE INTO documents VALUES (?,?,?,?)",
                    (doc.doc_id, rev, json.dumps(meta), now()),
                )
            col.delete(where={"$and": [{"doc_id": doc.doc_id}, {"revision": {"$ne": rev}}]})
            return "indexed"

    def remove(self, doc_id):
        with self.lock:
            with self.store.connect(write=True) as db:
                changed = db.execute("DELETE FROM documents WHERE id=?", (doc_id,)).rowcount
            self.collection.delete(where={"doc_id": doc_id})
            return bool(changed)

    def search(self, query, k=4, source_type=None, version=None):
        with self.lock:
            docs = [
                d
                for d in self.store.documents()
                if (not source_type or d["source_type"] == source_type)
                and (not version or d["version"] == version)
            ]
            if not docs:
                return []
            result = self.collection.query(
                query_embeddings=self.encoder.encode([query]),
                n_results=k * 3,
                where={"revision": {"$in": [d["revision"] for d in docs]}},
                include=["documents", "metadatas", "distances"],
            )
        evidence, seen = [], set()
        for cid, body, meta, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            if body in seen:
                continue
            seen.add(body)
            evidence.append(
                Evidence(
                    similarity=1.0 - float(distance),
                    chunk_id=cid,
                    excerpt=body[:1800],
                    **{
                        key: meta[key]
                        for key in ("doc_id", "title", "source_type", "url", "version", "section")
                    },
                )
            )
            if len(evidence) == k:
                break
        return evidence
