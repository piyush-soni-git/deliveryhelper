"""
grouping.py - Consistency-Checked Union-Find Clustering Engine.

Features:
- Disjoint-Set / Union-Find with path compression and union by rank.
- Consistency Check: Before merging two groups, verifies that NO pair across the two groups
  violates any hard conflict rule (e.g. conflicting flat numbers, different cities).
- Transitive Conflict Breaking: If a chain A ~ B ~ C has conflicting A and C,
  prevents single group merge, keeps B with the better match, and sends the other edge
  to the human Review Queue.
- Integration with Uncertainty Policy: Handles AUTO_MERGE, REVIEW, and SEPARATE tiers.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Any

from backend.extract import AddressComponents
from backend.scoring import calculate_similarity, MatchScoreResult
from backend.policy import Tier, PolicyThresholds, evaluate_tier


@dataclass
class ReviewQueueItem:
    id1: str
    id2: str
    address1: str
    address2: str
    score: float
    reason: str
    conflict_flags: List[str]
    components1: Dict[str, Any]
    components2: Dict[str, Any]
    decision: Optional[str] = None  # 'APPROVED', 'REJECTED', or None (pending)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id1": self.id1,
            "id2": self.id2,
            "address1": self.address1,
            "address2": self.address2,
            "score": round(self.score, 4),
            "reason": self.reason,
            "conflict_flags": self.conflict_flags,
            "components1": self.components1,
            "components2": self.components2,
            "decision": self.decision
        }


@dataclass
class ClusteringResult:
    record_to_group: Dict[str, str]
    groups: Dict[str, List[str]]
    review_queue: List[ReviewQueueItem]
    auto_merged_pairs: List[Tuple[str, str, float]]
    conflicting_pairs_blocked: List[Tuple[str, str, str]]


class ConsistencyUnionFind:
    def __init__(self, records: Dict[str, Dict[str, Any]]):
        """
        records: Dict[record_id, {'id': str, 'raw_address': str, 'normalized': str, 'components': AddressComponents}]
        """
        self.records = records
        self.parent: Dict[str, str] = {rid: rid for rid in records}
        self.rank: Dict[str, int] = {rid: 0 for rid in records}
        self.group_members: Dict[str, Set[str]] = {rid: {rid} for rid in records}

    def find(self, i: str) -> str:
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def has_conflict_between_groups(self, root1: str, root2: str) -> Tuple[bool, Optional[str], Optional[Tuple[str, str]]]:
        """
        Comprehensive consistency check:
        Verifies that NO member x in root1 conflicts with ANY member y in root2.
        """
        members1 = self.group_members[root1]
        members2 = self.group_members[root2]

        for m1 in members1:
            rec1 = self.records[m1]
            comp1: AddressComponents = rec1["components"]
            norm1: str = rec1["normalized"]

            for m2 in members2:
                rec2 = self.records[m2]
                comp2: AddressComponents = rec2["components"]
                norm2: str = rec2["normalized"]

                # Quick check: known conflicting flat numbers
                f1 = comp1.flat_no.value
                f2 = comp2.flat_no.value
                if f1 and f2 and f1.lower().replace("-", "").strip() != f2.lower().replace("-", "").strip():
                    return True, f"Hard Conflict: Member '{m1}' (Flat {f1}) and member '{m2}' (Flat {f2}) refer to different units.", (m1, m2)

                # Full check via calculate_similarity
                score_res = calculate_similarity(comp1, comp2, norm1, norm2)
                if score_res.has_hard_conflict:
                    flags_str = ", ".join(score_res.conflict_flags)
                    return True, f"Hard Conflict ({flags_str}) between members '{m1}' and '{m2}'.", (m1, m2)

        return False, None, None

    def union(self, i: str, j: str) -> bool:
        root_i = self.find(i)
        root_j = self.find(j)

        if root_i == root_j:
            return True

        # Union by rank
        if self.rank[root_i] < self.rank[root_j]:
            self.parent[root_i] = root_j
            self.group_members[root_j].update(self.group_members[root_i])
            del self.group_members[root_i]
        elif self.rank[root_i] > self.rank[root_j]:
            self.parent[root_j] = root_i
            self.group_members[root_i].update(self.group_members[root_j])
            del self.group_members[root_j]
        else:
            self.parent[root_j] = root_i
            self.group_members[root_i].update(self.group_members[root_j])
            del self.group_members[root_j]
            self.rank[root_i] += 1

        return True


def run_grouping(
    records: List[Dict[str, Any]],
    candidate_pairs: Set[Tuple[str, str]],
    thresholds: Optional[PolicyThresholds] = None,
    pre_calculated_scores: Optional[Dict[Tuple[str, str], MatchScoreResult]] = None
) -> ClusteringResult:
    """
    Executes consistency-checked clustering over candidate pairs.
    """
    threshold_cfg = thresholds or PolicyThresholds()
    record_map = {r["id"]: r for r in records}
    uf = ConsistencyUnionFind(record_map)

    # 1. Score all candidate pairs
    scored_edges: List[Tuple[float, str, str, MatchScoreResult, Tier, str]] = []
    scores_dict = pre_calculated_scores or {}

    for id1, id2 in candidate_pairs:
        pair_key = (min(id1, id2), max(id1, id2))
        if pair_key in scores_dict:
            res = scores_dict[pair_key]
        else:
            r1 = record_map[id1]
            r2 = record_map[id2]
            res = calculate_similarity(
                r1["components"], r2["components"],
                r1["normalized"], r2["normalized"]
            )
            scores_dict[pair_key] = res

        tier, tier_reason = evaluate_tier(res, threshold_cfg)
        scored_edges.append((res.score, id1, id2, res, tier, tier_reason))

    # 2. Sort candidate pairs by score descending (greedy best-match first)
    scored_edges.sort(key=lambda x: x[0], reverse=True)

    auto_merged_pairs: List[Tuple[str, str, float]] = []
    conflicting_blocked: List[Tuple[str, str, str]] = []
    review_queue: List[ReviewQueueItem] = []

    # 3. Process edges with consistency check
    for score, id1, id2, match_res, tier, tier_reason in scored_edges:
        root1 = uf.find(id1)
        root2 = uf.find(id2)

        if root1 == root2:
            continue

        # If tier is SEPARATE (hard conflict or low score), ignore
        if tier == Tier.SEPARATE:
            conflicting_blocked.append((id1, id2, tier_reason))
            continue

        # Consistency verification: verify no member in group1 conflicts with any member in group2
        has_conflict, conflict_reason, conflict_pair = uf.has_conflict_between_groups(root1, root2)

        if has_conflict:
            # Transitive conflict detected! Break chain, block merge, route to review
            conflicting_blocked.append((id1, id2, conflict_reason or "Transitive Conflict"))
            review_queue.append(ReviewQueueItem(
                id1=id1,
                id2=id2,
                address1=record_map[id1]["raw_address"],
                address2=record_map[id2]["raw_address"],
                score=score,
                reason=f"Transitive Conflict: {conflict_reason}",
                conflict_flags=match_res.conflict_flags + ["TRANSITIVE_CHAIN_CONFLICT"],
                components1=record_map[id1]["components"].to_dict(),
                components2=record_map[id2]["components"].to_dict()
            ))
            continue

        # If edge is tier AUTO_MERGE and clean, merge!
        if tier == Tier.AUTO_MERGE:
            uf.union(root1, root2)
            auto_merged_pairs.append((id1, id2, score))
        elif tier == Tier.REVIEW:
            # Route to human review queue
            review_queue.append(ReviewQueueItem(
                id1=id1,
                id2=id2,
                address1=record_map[id1]["raw_address"],
                address2=record_map[id2]["raw_address"],
                score=score,
                reason=tier_reason,
                conflict_flags=match_res.conflict_flags,
                components1=record_map[id1]["components"].to_dict(),
                components2=record_map[id2]["components"].to_dict()
            ))

    # Construct final output structures
    record_to_group: Dict[str, str] = {}
    groups: Dict[str, List[str]] = defaultdict(list)

    for rid in record_map:
        root = uf.find(rid)
        group_id = f"GRP_{root}"
        record_to_group[rid] = group_id
        groups[group_id].append(rid)

    return ClusteringResult(
        record_to_group=record_to_group,
        groups=dict(groups),
        review_queue=review_queue,
        auto_merged_pairs=auto_merged_pairs,
        conflicting_pairs_blocked=conflicting_blocked
    )
