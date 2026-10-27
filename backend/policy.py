"""
policy.py - Uncertainty Policy and Tier Decision Engine.

Three Tiers (thresholds dynamically configurable):
- AUTO_MERGE: score >= 0.90, no conflicts, not uncertain
- REVIEW: 0.70 <= score < 0.90 OR missing critical field (e.g. flat number)
- SEPARATE: score < 0.70 OR any hard conflict
"""

from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Dict, Any

from backend.scoring import MatchScoreResult


class Tier(str, Enum):
    AUTO_MERGE = "AUTO_MERGE"
    REVIEW = "REVIEW"
    SEPARATE = "SEPARATE"


@dataclass
class PolicyThresholds:
    threshold_auto: float = 0.90
    threshold_review: float = 0.70

    def to_dict(self) -> Dict[str, float]:
        return {
            "threshold_auto": self.threshold_auto,
            "threshold_review": self.threshold_review
        }


def evaluate_tier(
    match_result: MatchScoreResult,
    thresholds: PolicyThresholds
) -> Tuple[Tier, str]:
    """
    Evaluates tier classification based on score, uncertainty, and conflict flags.
    """
    if match_result.has_hard_conflict:
        return Tier.SEPARATE, "Hard conflict detected (e.g. different flat numbers or cities); merging prohibited."

    if match_result.is_uncertain:
        if match_result.score >= thresholds.threshold_review:
            return Tier.REVIEW, "Missing critical field (e.g. flat number); routed to human review for verification."
        else:
            return Tier.SEPARATE, "Missing critical field and composite similarity below review threshold."

    if match_result.score >= thresholds.threshold_auto:
        return Tier.AUTO_MERGE, f"High component similarity ({round(match_result.score, 2)}) with no conflicts."

    if match_result.score >= thresholds.threshold_review:
        return Tier.REVIEW, f"Moderate similarity ({round(match_result.score, 2)}) requires human review."

    return Tier.SEPARATE, f"Similarity ({round(match_result.score, 2)}) is below the {thresholds.threshold_review} threshold."
