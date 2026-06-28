from typing import Dict, Tuple


def compute_coverage_score(required_fields_status: Dict[str, bool]) -> float:
    if not required_fields_status:
        return 0.0
    total = len(required_fields_status)
    completed = sum(1 for ok in required_fields_status.values() if ok)
    return round(completed / total, 3)


def compute_confidence(intent_score: float, coverage_score: float) -> float:
    confidence = (0.6 * float(intent_score)) + (0.4 * float(coverage_score))
    return round(max(0.0, min(1.0, confidence)), 3)


def detect_case_conflict(best_score: float, second_score: float, conflict_delta: float) -> bool:
    if best_score <= 0:
        return False
    return abs(best_score - second_score) <= conflict_delta


def evaluate_confidence(
    *,
    intent_score: float,
    required_fields_status: Dict[str, bool],
    threshold: float,
) -> Tuple[float, bool]:
    coverage = compute_coverage_score(required_fields_status)
    confidence = compute_confidence(intent_score, coverage)
    return confidence, confidence >= threshold
