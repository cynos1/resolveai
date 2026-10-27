from src.database_tools import get_booking_baggage
from src.policy_retrieval import search_policy


def investigate_booking(
    booking_reference,
    question,
    database_path,
    policy_path,
    top_k=3
):
    """
    Collect booking and policy evidence
    for a customer-support investigation.
    """

    booking = get_booking_baggage(
        booking_reference,
        database_path=database_path
    )

    if not booking["found"]:
        return None

    policy_results = search_policy(
        query=question,
        policy_path=policy_path,
        top_k=top_k
    )

    return {
        "booking_reference": booking_reference,
        "question": question,
        "booking": booking,
        "policy_evidence": policy_results
    }

