def precision_at_k(retrieved_titles: list, expected_titles: list, k: int) -> float:
    if not retrieved_titles or k == 0:
        return 0.0
    top_k = retrieved_titles[:k]
    relevant_count = sum(1 for t in top_k if t in expected_titles)
    return relevant_count / k

def recall_at_k(retrieved_titles: list, expected_titles: list, k: int) -> float:
    if not expected_titles:
        return 1.0 # If we didn't expect anything, recall is perfect
    if not retrieved_titles or k == 0:
        return 0.0
    top_k = retrieved_titles[:k]
    relevant_count = sum(1 for t in top_k if t in expected_titles)
    return relevant_count / len(expected_titles)

def mrr(retrieved_titles: list, expected_titles: list) -> float:
    if not expected_titles:
        return 1.0
    for i, title in enumerate(retrieved_titles):
        if title in expected_titles:
            return 1.0 / (i + 1)
    return 0.0

def evidence_hit_rate(retrieved_titles: list, expected_titles: list) -> bool:
    if not expected_titles:
        return True
    return any(t in expected_titles for t in retrieved_titles)

def check_groundedness(answer: str, evidence: list, expected_no_evidence: bool = False) -> bool:
    """
    Engineering groundedness checks:
    1. Answer generated with no evidence when threshold failed.
    2. Answer generated when evidence is empty.
    """
    if not evidence and not expected_no_evidence:
        # If we have no evidence, the answer should explicitly state no verified info
        return "verified medical information" in answer.lower()
    if evidence and expected_no_evidence:
        return False
    return True

