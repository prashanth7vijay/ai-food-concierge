"""
Semantic retrieval support.

Real deployments would call an embedding model (e.g. Gemini's
text-embedding-004) at ingestion time and store vectors in pgvector, then
do the same at query time and run an ANN search in Postgres.

For this project to be runnable/testable without external API credentials,
`HashingEmbeddingProvider` computes a deterministic, offline bag-of-words
hashing embedding (a standard cheap-embedding technique, similar in spirit
to feature hashing used in classic NLP). It captures token overlap well
enough to demo "something light for dinner" style queries, but it is not a
learned embedding — see README trade-offs for what upgrading to a real
provider would change (mainly: swap `EmbeddingProvider` implementation,
nothing else in the retrieval pipeline needs to change).
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from backend.core.config import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A tiny synonym map so common natural-language descriptors connect to the
# domain vocabulary they conceptually relate to. This is a deliberate,
# documented heuristic — not a learned association.
_SYNONYMS: dict[str, list[str]] = {
    "light": ["salad", "soup", "steamed", "grilled", "clear", "broth"],
    "heavy": ["fried", "creamy", "rich", "butter", "cheese"],
    "comforting": ["curry", "dal", "khichdi", "soup", "stew"],
    "healthy": ["salad", "grilled", "steamed", "millet", "sprouts"],
    "filling": ["rice", "biryani", "thali", "paratha", "roti"],
    "dinner": ["curry", "biryani", "thali", "roti"],
    "breakfast": ["idli", "dosa", "poha", "upma"],
}


def _tokenize(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    expanded = list(tokens)
    for t in tokens:
        expanded.extend(_SYNONYMS.get(t, []))
    return expanded


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class HashingEmbeddingProvider:
    def __init__(self, dim: int | None = None):
        self.dim = dim or get_settings().EMBEDDING_DIM

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for token in tokens:
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    return max(0.0, min(1.0, (dot + 1) / 2))  # rescale [-1,1] -> [0,1]


_default_provider = HashingEmbeddingProvider()


def get_embedding_provider() -> EmbeddingProvider:
    return _default_provider
