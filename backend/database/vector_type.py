"""
Portable embedding-vector column type.

On PostgreSQL we use the `pgvector` extension's native `VECTOR` type, which
supports fast approximate-nearest-neighbor search via an ivfflat/hnsw index.

On SQLite (used for local dev/tests without installing Postgres) there is no
native vector type or ANN index, so we fall back to storing the embedding as
a JSON-encoded float array and compute cosine similarity in Python. This is
fine for a demo dataset (dozens of items) but would not scale — that's the
whole reason production uses pgvector; see README trade-offs section.
"""

from __future__ import annotations

import json

from sqlalchemy import String, TypeDecorator

from backend.core.config import get_settings

try:
    from pgvector.sqlalchemy import Vector as _PgVector

    _HAS_PGVECTOR = True
except ImportError:  # pgvector driver not installed (e.g. SQLite-only dev env)
    _HAS_PGVECTOR = False


class EmbeddingVector(TypeDecorator):
    """Stores a fixed-dimension float embedding."""

    impl = String
    cache_ok = True

    def __init__(self, dim: int | None = None, *args, **kwargs):
        self.dim = dim or get_settings().EMBEDDING_DIM
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return dialect.type_descriptor(_PgVector(self.dim))
        return dialect.type_descriptor(String())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return value
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return value
        return json.loads(value)
