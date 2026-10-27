import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from src.policy_retrieval import POLICY_PATH
from src.hybrid_retrieval import load_retrievable_sections
from src.semantic_retrieval import (
    EMBEDDING_MODEL,
    embed_texts,
    rank_sections,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INDEX_PATH = (
    PROJECT_ROOT / "data" / "database" / "policy_embeddings.json"
)

INDEX_VERSION = 1


def policy_fingerprint(policy_path):
    """Hash the exact policy document bytes."""

    document_bytes = Path(policy_path).read_bytes()

    return hashlib.sha256(document_bytes).hexdigest()


def build_index(
    policy_path=POLICY_PATH,
    model=EMBEDDING_MODEL,
    embedder=embed_texts,
):
    """Build a new policy embedding index."""

    sections = load_retrievable_sections(policy_path)

    if not sections:
        raise ValueError("Policy contains no retrievable sections")

    section_texts = [
        section["heading"] + "\n" + section["content"]
        for section in sections
    ]

    embeddings = embedder(section_texts)

    if len(embeddings) != len(sections):
        raise ValueError("Embedding count mismatch")

    dimensions = len(embeddings[0])

    if dimensions == 0:
        raise ValueError("Embedding vectors cannot be empty")

    for vector in embeddings:
        if len(vector) != dimensions:
            raise ValueError("Inconsistent embedding dimensions")

        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in vector
        ):
            raise ValueError("Invalid embedding values")

        if not any(value != 0 for value in vector):
            raise ValueError("Embedding vector cannot be zero")

    return {
        "index_version": INDEX_VERSION,
        "embedding_model": model,
        "policy_fingerprint": policy_fingerprint(policy_path),
        "dimensions": dimensions,
        "sections": sections,
        "embeddings": embeddings,
    }


def save_index(index, index_path=INDEX_PATH):
    """Atomically save an index to disk."""

    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=index_path.parent,
            prefix=".policy-index-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            json.dump(index, temporary_file, indent=2)

            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, index_path)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_index(index_path=INDEX_PATH):
    """Read an existing index from disk."""

    return json.loads(
        Path(index_path).read_text(encoding="utf-8")
    )


def index_is_valid(
    index,
    policy_path=POLICY_PATH,
    model=EMBEDDING_MODEL,
):
    """Check whether a saved index can be reused."""

    if not isinstance(index, dict):
        return False

    if index.get("index_version") != INDEX_VERSION:
        return False

    if index.get("embedding_model") != model:
        return False

    if index.get("policy_fingerprint") != policy_fingerprint(
        policy_path
    ):
        return False

    sections = index.get("sections")
    embeddings = index.get("embeddings")
    dimensions = index.get("dimensions")

    if not isinstance(sections, list) or not sections:
        return False

    if not isinstance(embeddings, list):
        return False

    if len(sections) != len(embeddings):
        return False

    if (
        not isinstance(dimensions, int)
        or isinstance(dimensions, bool)
        or dimensions < 1
    ):
        return False

    for section, vector in zip(sections, embeddings):
        if not isinstance(section, dict):
            return False

        if not isinstance(section.get("heading"), str):
            return False

        if not isinstance(section.get("content"), str):
            return False

        if not isinstance(vector, list):
            return False

        if len(vector) != dimensions:
            return False

        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in vector
        ):
            return False

        if not any(value != 0 for value in vector):
            return False

    return True


def get_or_build_index(
    policy_path=POLICY_PATH,
    index_path=INDEX_PATH,
    model=EMBEDDING_MODEL,
    embedder=embed_texts,
):
    """
    Reuse a valid index or rebuild a missing/stale index.

    Returns:
        (index, status)
    """

    try:
        index = load_index(index_path)

        if index_is_valid(index, policy_path, model):
            return index, "reused"

    except (FileNotFoundError, json.JSONDecodeError, UnicodeError):
        pass

    index = build_index(
        policy_path=policy_path,
        model=model,
        embedder=embedder,
    )

    save_index(index, index_path)

    return index, "rebuilt"


def search_persistent_index(
    query,
    index,
    top_k=3,
    embedder=embed_texts,
):
    """Search a previously loaded policy index."""

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if not query.strip():
        return []

    query_vectors = embedder([query])

    if len(query_vectors) != 1:
        raise ValueError("Expected one query embedding")

    query_vector = query_vectors[0]

    if len(query_vector) != index["dimensions"]:
        raise ValueError(
            "Query embedding dimension does not match index"
        )

    return rank_sections(
        query_vector,
        index["sections"],
        index["embeddings"],
        top_k=top_k,
    )
