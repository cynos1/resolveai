from src.policy_retrieval import search_policy


def evaluate_query(
    query,
    relevant_headings,
    policy_path,
    top_k=3
):
    """
    Evaluate one retrieval query against known
    relevant policy section headings.
    """

    if not relevant_headings:
        raise ValueError(
            "Each evaluation query needs at least one "
            "relevant heading"
        )

    results = search_policy(
        query=query,
        policy_path=policy_path,
        top_k=top_k
    )

    retrieved_headings = [
        result["heading"] for result in results
    ]

    relevant = set(relevant_headings)

    # Find the rank of the first relevant result.
    first_relevant_rank = None

    for rank, heading in enumerate(
        retrieved_headings,
        start=1
    ):
        if heading in relevant:
            first_relevant_rank = rank
            break

    hit = int(first_relevant_rank is not None)

    reciprocal_rank = (
        1 / first_relevant_rank
        if first_relevant_rank is not None
        else 0.0
    )

    return {
        "query": query,
        "relevant_headings": sorted(relevant),
        "retrieved_headings": retrieved_headings,
        "hit": hit,
        "reciprocal_rank": reciprocal_rank
    }


def evaluate_dataset(
    dataset,
    policy_path,
    top_k=3
):
    """
    Evaluate multiple labeled retrieval queries.
    """

    if not dataset:
        raise ValueError(
            "Evaluation dataset cannot be empty"
        )

    evaluations = []

    for example in dataset:
        result = evaluate_query(
            query=example["query"],
            relevant_headings=example[
                "relevant_headings"
            ],
            policy_path=policy_path,
            top_k=top_k
        )

        evaluations.append(result)

    hit_rate = sum(
        result["hit"] for result in evaluations
    ) / len(evaluations)

    mrr = sum(
        result["reciprocal_rank"]
        for result in evaluations
    ) / len(evaluations)

    return {
        "total_queries": len(evaluations),
        "top_k": top_k,
        "hit_rate": hit_rate,
        "mrr": mrr,
        "results": evaluations
    }
