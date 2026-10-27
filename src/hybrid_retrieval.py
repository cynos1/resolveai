import re

from src.policy_retrieval import (
    POLICY_PATH,
    load_policy,
    split_into_sections,
    tokenize,
)

from src.semantic_retrieval import (
    embed_texts,
    rank_sections,
)


def load_retrievable_sections(policy_path=POLICY_PATH):
    """
    Load policy sections, excluding the document title.
    """

    document = load_policy(policy_path)
    sections = split_into_sections(document)

    # Identify the first Markdown level-one heading.
    title = None

    for line in document.splitlines():
        if not line.strip():
            continue

        match = re.match(r"^#\s+(.+?)\s*$", line)

        if match:
            title = match.group(1).strip()

        break

    if title:
        sections = [
            section for section in sections
            if section["heading"] != title
        ]

    return sections


def keyword_rank(query, sections, top_k=None):
    """
    Rank sections using keyword overlap.
    """

    if top_k is not None and top_k < 1:
        raise ValueError("top_k must be at least 1")

    query_terms = tokenize(query)

    if not query_terms:
        return []

    results = []

    for section in sections:
        searchable_text = (
            section["heading"] + " " + section["content"]
        )

        section_terms = tokenize(searchable_text)

        score = len(query_terms & section_terms)

        if score > 0:
            results.append({
                "heading": section["heading"],
                "content": section["content"],
                "score": score,
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if top_k is None:
        return results

    return results[:top_k]


def reciprocal_rank_fusion(
    ranking_lists,
    top_k=3,
    rrf_k=60,
):
    """
    Combine multiple ranked result lists using RRF.
    """

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if rrf_k < 0:
        raise ValueError("rrf_k cannot be negative")

    scores = {}
    documents = {}

    for ranking in ranking_lists:
        seen = set()

        for rank, result in enumerate(ranking, start=1):
            heading = result["heading"]

            # Avoid counting the same document twice
            # within a single ranking.
            if heading in seen:
                continue

            seen.add(heading)

            documents[heading] = {
                "heading": heading,
                "content": result["content"],
            }

            scores[heading] = (
                scores.get(heading, 0.0)
                + 1.0 / (rrf_k + rank)
            )

    combined = []

    for heading, document in documents.items():
        combined.append({
            **document,
            "score": scores[heading],
        })

    combined.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return combined[:top_k]


def hybrid_search(
    query,
    sections,
    section_embeddings,
    top_k=3,
):
    """
    Combine keyword and semantic retrieval.
    """

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if not query.strip():
        return []

    query_embedding = embed_texts([query])[0]

    keyword_results = keyword_rank(
        query,
        sections,
    )

    semantic_results = rank_sections(
        query_embedding,
        sections,
        section_embeddings,
        top_k=len(sections),
    )

    return reciprocal_rank_fusion(
        [keyword_results, semantic_results],
        top_k=top_k,
    )
