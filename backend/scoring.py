"""
scoring.py - Component-Aware Address Similarity Scoring and Conflict Verification.

Rules:
- Per-component similarity (RapidFuzz) with configurable weights.
- HARD CONFLICT RULES:
  1. Two known, different flat numbers => NEVER MERGE (Score = 0.0, has_hard_conflict = True)
  2. Different known buildings => Strong penalty (-0.40) or veto if completely distinct
  3. PIN mismatch => Soft penalty only (-0.05)
  4. Missing critical field (e.g. flat_no) => mark "is_uncertain = True" (route to review, not auto-match)
- Output: Score, per-component breakdown, and conflict flags.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from rapidfuzz import fuzz

from backend.extract import AddressComponents


@dataclass
class MatchScoreResult:
    score: float
    breakdown: Dict[str, Optional[float]]
    conflict_flags: List[str]
    has_hard_conflict: bool
    is_uncertain: bool
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "breakdown": {k: (round(v, 4) if v is not None else None) for k, v in self.breakdown.items()},
            "conflict_flags": self.conflict_flags,
            "has_hard_conflict": self.has_hard_conflict,
            "is_uncertain": self.is_uncertain,
            "explanation": self.explanation
        }


DEFAULT_WEIGHTS = {
    "building": 0.30,
    "road": 0.20,
    "locality": 0.15,
    "city": 0.15,
    "full_text": 0.20,
}


def normalize_flat_token(val: Optional[str]) -> Optional[str]:
    """Normalizes flat identifiers: removes leading zeros, hyphens e.g. '0402' -> '402', 'a-101' -> 'a101'."""
    if not val:
        return None
    cleaned = val.lower().replace("-", "").replace("/", "").replace(" ", "").lstrip("0")
    return cleaned or "0"


def calculate_similarity(
    comp1: AddressComponents,
    comp2: AddressComponents,
    norm1: str,
    norm2: str,
    weights: Optional[Dict[str, float]] = None,
    building_penalty: float = 0.40,
    pin_penalty: float = 0.05,
) -> MatchScoreResult:
    """
    Computes component-aware similarity score and verifies conflict constraints.
    """
    active_weights = (weights or DEFAULT_WEIGHTS).copy()
    conflict_flags: List[str] = []
    has_hard_conflict = False
    is_uncertain = False
    explanations: List[str] = []

    f1 = comp1.flat_no.value
    f2 = comp2.flat_no.value
    fn1 = normalize_flat_token(f1)
    fn2 = normalize_flat_token(f2)

    # -------------------------------------------------------------
    # 1. HARD CONFLICT: Flat Number Check
    # -------------------------------------------------------------
    flat_sim: Optional[float] = None
    if fn1 is not None and fn2 is not None:
        if fn1 == fn2:
            flat_sim = 1.0
            explanations.append(f"Identical flat number confirmed: '{f1}'.")
        else:
            # Absolute hard conflict: two different known flat numbers in the same structure!
            has_hard_conflict = True
            conflict_flags.append("HARD_CONFLICT_DIFFERENT_FLATS")
            explanations.append(f"Hard Conflict: Conflicting flat numbers '{f1}' vs '{f2}'. Cannot merge.")
            return MatchScoreResult(
                score=0.0,
                breakdown={"flat": 0.0, "building": 0.0, "road": 0.0, "locality": 0.0, "city": 0.0, "pin": 0.0, "full_text": 0.0},
                conflict_flags=conflict_flags,
                has_hard_conflict=True,
                is_uncertain=False,
                explanation="; ".join(explanations)
            )
    else:
        # One or both flat numbers are missing
        is_uncertain = True
        conflict_flags.append("MISSING_CRITICAL_FIELD_FLAT")
        explanations.append("One or both records lack an explicit flat number; cannot definitively prove same delivery unit.")

    # -------------------------------------------------------------
    # 2. City Check
    # -------------------------------------------------------------
    city1 = comp1.city.value
    city2 = comp2.city.value
    city_sim: Optional[float] = None
    if city1 and city2:
        if city1.lower() == city2.lower():
            city_sim = 1.0
        else:
            # Known different cities => hard conflict
            has_hard_conflict = True
            conflict_flags.append("HARD_CONFLICT_DIFFERENT_CITIES")
            explanations.append(f"Hard Conflict: Different cities '{city1}' vs '{city2}'.")
            return MatchScoreResult(
                score=0.0,
                breakdown={"flat": flat_sim, "building": 0.0, "road": 0.0, "locality": 0.0, "city": 0.0, "pin": 0.0, "full_text": 0.0},
                conflict_flags=conflict_flags,
                has_hard_conflict=True,
                is_uncertain=False,
                explanation="; ".join(explanations)
            )

    # -------------------------------------------------------------
    # 3. Building Similarity and Conflict Check
    # -------------------------------------------------------------
    b1 = comp1.building.value
    b2 = comp2.building.value
    bldg_sim: Optional[float] = None
    applied_penalties = 0.0

    if b1 and b2:
        bldg_sim = fuzz.token_sort_ratio(b1, b2) / 100.0
        if bldg_sim >= 0.85:
            explanations.append(f"Strong building match: '{b1}' ~ '{b2}' ({int(bldg_sim*100)}%).")
        elif bldg_sim < 0.50 and comp1.building.confidence >= 0.8 and comp2.building.confidence >= 0.8:
            # Different known buildings => strong penalty
            conflict_flags.append("BUILDING_MISMATCH_STRONG_PENALTY")
            applied_penalties += building_penalty
            explanations.append(f"Building mismatch penalty (-{building_penalty}): '{b1}' vs '{b2}' ({int(bldg_sim*100)}%).")
    elif not b1 and not b2:
        is_uncertain = True
        conflict_flags.append("MISSING_BUILDING_FIELD")

    # -------------------------------------------------------------
    # 4. Road Similarity
    # -------------------------------------------------------------
    r1 = comp1.road.value
    r2 = comp2.road.value
    road_sim: Optional[float] = None
    if r1 and r2:
        road_sim = fuzz.token_set_ratio(r1, r2) / 100.0

    # -------------------------------------------------------------
    # 5. Locality Similarity
    # -------------------------------------------------------------
    loc1 = comp1.locality.value
    loc2 = comp2.locality.value
    loc_sim: Optional[float] = None
    if loc1 and loc2:
        loc_sim = fuzz.token_set_ratio(loc1, loc2) / 100.0

    # -------------------------------------------------------------
    # 6. PIN Check (Soft Penalty on Mismatch)
    # -------------------------------------------------------------
    p1 = comp1.pin.value
    p2 = comp2.pin.value
    pin_sim: Optional[float] = None
    if p1 and p2:
        if p1 == p2:
            pin_sim = 1.0
            explanations.append(f"PIN match: {p1}.")
        else:
            # Soft penalty only (common typos or neighboring postal sub-zones)
            pin_sim = 0.0
            applied_penalties += pin_penalty
            conflict_flags.append("PIN_MISMATCH_SOFT_PENALTY")
            explanations.append(f"Soft penalty (-{pin_penalty}): PIN mismatch {p1} vs {p2}.")

    # -------------------------------------------------------------
    # 7. Full-Text Fallback Similarity
    # -------------------------------------------------------------
    full_text_sim = fuzz.token_set_ratio(norm1, norm2) / 100.0

    # -------------------------------------------------------------
    # 8. Weighted Score Aggregation
    # -------------------------------------------------------------
    available_scores = {
        "building": bldg_sim,
        "road": road_sim,
        "locality": loc_sim,
        "city": city_sim,
        "full_text": full_text_sim
    }

    # Normalize weights among present fields
    total_active_weight = 0.0
    accumulated_score = 0.0
    for field_name, sim_val in available_scores.items():
        if sim_val is not None:
            w = active_weights.get(field_name, 0.20)
            total_active_weight += w
            accumulated_score += (sim_val * w)

    base_score = (accumulated_score / total_active_weight) if total_active_weight > 0 else full_text_sim

    # Deduct penalties
    final_score = max(0.0, min(1.0, base_score - applied_penalties))

    breakdown = {
        "flat": flat_sim,
        "building": bldg_sim,
        "road": road_sim,
        "locality": loc_sim,
        "city": city_sim,
        "pin": pin_sim,
        "full_text": full_text_sim,
    }

    if not explanations:
        explanations.append(f"Calculated composite similarity: {round(final_score, 2)}.")

    return MatchScoreResult(
        score=final_score,
        breakdown=breakdown,
        conflict_flags=conflict_flags,
        has_hard_conflict=has_hard_conflict,
        is_uncertain=is_uncertain,
        explanation="; ".join(explanations)
    )
