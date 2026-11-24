"""Prime the pinned Sentence Transformers snapshot before running offline."""

from backend.config import Settings
from backend.index import Encoder

if __name__ == "__main__":
    print("Embedding dimensions:", len(Encoder(Settings()).encode(["FastAPI validation"])[0]))
