"""
representative.py - Canonical Record and Consensus Representation Selector.

Rules:
- Pick the most complete, most frequent REAL record in the group.
- Build a structured consensus representation from fields that actually appear across group members.
- NEVER invent or hallucinate missing details.
"""

from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

from backend.extract import AddressComponents


@dataclass
class GroupRepresentation:
    group_id: str
    representative_record_id: str
    representative_address: str
    member_count: int
    member_ids: List[str]
    consensus_components: Dict[str, Optional[str]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "representative_record_id": self.representative_record_id,
            "representative_address": self.representative_address,
            "member_count": self.member_count,
            "member_ids": self.member_ids,
            "consensus_components": self.consensus_components,
        }


def select_representative(
    group_id: str,
    member_records: List[Dict[str, Any]]
) -> GroupRepresentation:
    """
    Selects the most complete, most frequent real record in the group,
    and produces a consensus component dictionary of fields that actually appear.
    """
    if not member_records:
        raise ValueError("Cannot select representative for an empty group.")

    if len(member_records) == 1:
        rec = member_records[0]
        comp: AddressComponents = rec["components"]
        return GroupRepresentation(
            group_id=group_id,
            representative_record_id=rec["id"],
            representative_address=rec["raw_address"],
            member_count=1,
            member_ids=[rec["id"]],
            consensus_components={
                "flat_no": comp.flat_no.value,
                "building": comp.building.value,
                "road": comp.road.value,
                "locality": comp.locality.value,
                "city": comp.city.value,
                "pin": comp.pin.value,
            }
        )

    # 1. Collect frequency counts for each component across all members
    counters = {
        "flat_no": Counter(),
        "building": Counter(),
        "road": Counter(),
        "locality": Counter(),
        "city": Counter(),
        "pin": Counter(),
    }

    for rec in member_records:
        comp: AddressComponents = rec["components"]
        if comp.flat_no.value:
            counters["flat_no"][comp.flat_no.value] += 1
        if comp.building.value:
            counters["building"][comp.building.value] += 1
        if comp.road.value:
            counters["road"][comp.road.value] += 1
        if comp.locality.value:
            counters["locality"][comp.locality.value] += 1
        if comp.city.value:
            counters["city"][comp.city.value] += 1
        if comp.pin.value:
            counters["pin"][comp.pin.value] += 1

    consensus_components: Dict[str, Optional[str]] = {}
    for field_name, counter in counters.items():
        if counter:
            # Most common non-None value that appeared in real records
            consensus_components[field_name] = counter.most_common(1)[0][0]
        else:
            consensus_components[field_name] = None

    # 2. Score each REAL record to find the best representative
    best_record = None
    best_score = -1.0

    for rec in member_records:
        comp: AddressComponents = rec["components"]
        score = 0.0

        # Completeness points
        fields = [
            comp.flat_no, comp.building, comp.road,
            comp.locality, comp.city, comp.pin
        ]
        non_empty_count = sum(1 for f in fields if f.value is not None)
        score += non_empty_count * 10.0

        # Confidence sum
        confidence_sum = sum(f.confidence for f in fields)
        score += confidence_sum * 2.0

        # Consensus alignment points
        if comp.flat_no.value == consensus_components["flat_no"] and comp.flat_no.value is not None:
            score += 5.0
        if comp.building.value == consensus_components["building"] and comp.building.value is not None:
            score += 5.0
        if comp.road.value == consensus_components["road"] and comp.road.value is not None:
            score += 4.0
        if comp.city.value == consensus_components["city"] and comp.city.value is not None:
            score += 3.0
        if comp.pin.value == consensus_components["pin"] and comp.pin.value is not None:
            score += 4.0

        # Tie-breaker: prefer cleaner / moderately detailed raw text
        raw_len = len(rec["raw_address"])
        if 20 <= raw_len <= 120:
            score += 1.0

        if score > best_score:
            best_score = score
            best_record = rec

    chosen = best_record or member_records[0]

    return GroupRepresentation(
        group_id=group_id,
        representative_record_id=chosen["id"],
        representative_address=chosen["raw_address"],
        member_count=len(member_records),
        member_ids=[r["id"] for r in member_records],
        consensus_components=consensus_components
    )
