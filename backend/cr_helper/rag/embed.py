"""Text embeddings. Offline feature-hashing default; Voyage for production."""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from ..config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "to", "of", "and", "or", "in", "on", "is", "it", "your", "you",
    "with", "for", "at", "be", "this", "that", "as", "if", "by", "but", "are", "can",
}


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in _STOP]


def _bucket(token: str, dim: int) -> tuple[int, int]:
    d = hashlib.md5(token.encode()).digest()
    idx = int.from_bytes(d[:4], "little") % dim
    sign = 1 if d[4] & 1 else -1
    return idx, sign


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


def cosine(a: list[float], b: list[float]) -> float:
    """Dot product (vectors are stored L2-normalized, so this is cosine similarity)."""
    return sum(x * y for x, y in zip(a, b))


class Embedder(ABC):
    name: str = "abstract"
    dim: int = 0

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class HashingEmbedder(Embedder):
    """Deterministic, dependency-free feature-hashing embedding (lexical similarity).

    Uses a stable hash (md5) — NOT Python's randomized hash() — so stored chunk
    vectors and query vectors are comparable across processes. Good enough to
    demonstrate grounded retrieval offline; production should use Voyage / a bge model.
    """

    def __init__(self, dim: int | None = None):
        self.dim = dim or settings.embed_dim
        self.name = f"hashing-v1-{self.dim}"

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _tokens(text):
            idx, sign = _bucket(tok, self.dim)
            vec[idx] += sign
        return _normalize(vec)


class VoyageEmbedder(Embedder):
    """Production embeddings via Voyage AI (Anthropic-recommended). Needs VOYAGE_API_KEY."""

    def __init__(self, model: str = "voyage-3-large"):
        import voyageai

        self._client = voyageai.Client(api_key=settings.voyage_api_key or None)
        self.model = model
        self.name = f"voyage:{model}"
        self.dim = 1024

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        res = self._client.embed(list(texts), model=self.model, input_type="document")
        return [_normalize(v) for v in res.embeddings]


def get_embedder() -> Embedder:
    if settings.embed_backend == "voyage":
        return VoyageEmbedder()
    return HashingEmbedder()
