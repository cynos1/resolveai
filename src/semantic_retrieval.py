import math

import requests

from src.policy_retrieval import (
    POLICY_PATH,
    load_policy,
    split_into_sections,
)


OLLAMA_URL = "http://localhost:11434/api/embed"
EMBEDDING_MODEL = "qwen3-embedding:4b"


def embed_texts(texts):
    """Generate embeddings using local Ollama."""

    if not texts:
        return []

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": EMBEDDING_MODEL,
            "input": texts,
        },
        timeout=180,
    )

    response.raise_for_status()

    embeddings = response.json()["embeddings"]

    if len(embeddings) != len(texts):
        raise ValueError(
            "Embedding count does not match input count"
        )

    return embeddings


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two vectors."""

    if not vector_a or not vector_b:
        raise ValueError("Vectors cannot be empty")

    if len(vector_a) != len(vector_b):
        raise ValueError("Vector dimensions must match")

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        raise ValueError("Cannot compare zero vectors")

    return dot_product / (
        magnitude_a * magnitude_b
    )


def rank_sections(query_embedding, sections, section_embeddings, top_k=3):
    """Rank policy sections using cosine similarity."""

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if len(sections) != len(section_embeddings):
        raise ValueError(
            "Section and embedding counts must match"
        )

    results = []

    for section, embedding in zip(
        sections, section_embeddings
    ):
        score = cosine_similarity(
            query_embedding,
            embedding
        )

        results.append({
            "heading": section["heading"],
            "content": section["content"],
            "score": score,
        })

    results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    return results[:top_k]


def prepare_policy_embeddings(policy_path=POLICY_PATH):
    """Load and embed policy sections once."""

    document = load_policy(policy_path)
    sections = split_into_sections(document)

    section_texts = [
        section["heading"] + "\n" + section["content"]
        for section in sections
    ]

    section_embeddings = embed_texts(section_texts)

    return sections, section_embeddings


def semantic_search(
    query,
    sections,
    section_embeddings,
    top_k=3
):
    """Retrieve policy sections by semantic similarity."""

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if not query.strip():
        return []

    query_embedding = embed_texts([query])[0]

    return rank_sections(
        query_embedding,
        sections,
        section_embeddings,
        top_k=top_k
    )
