import pytest
from backend.normalize import normalize_address
from backend.extract import extract_components
from backend.blocking import BlockingEngine
from backend.grouping import run_grouping, ConsistencyUnionFind
from backend.policy import PolicyThresholds


def test_canonical_reference_a101_to_a104():
    """
    Requirement from prompt:
    Ship the exact example set: A101-A104 (Lotus Apartments, JLN Road, Jaipur)
    must give Group 1 = A101, A102, A104; Group 2 = A103.
    """
    samples = [
        {"id": "A101", "raw_address": "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"},
        {"id": "A102", "raw_address": "402, Lotus Apts, JLN Marg, Jaipur - 302017"},
        {"id": "A103", "raw_address": "Flat 403, Lotus Apartments, JLN Road, Jaipur 302017"},
        {"id": "A104", "raw_address": "Apt #402, Lotus Appts, Near WTP, JLN Rd, Jaipur"}
    ]
    for s in samples:
        s["normalized"] = normalize_address(s["raw_address"])
        s["components"] = extract_components(s["normalized"])

    engine = BlockingEngine()
    b_res = engine.generate_candidate_pairs(samples)
    clustering = run_grouping(samples, b_res.candidate_pairs)

    group_of_a101 = clustering.record_to_group["A101"]
    group_of_a102 = clustering.record_to_group["A102"]
    group_of_a103 = clustering.record_to_group["A103"]
    group_of_a104 = clustering.record_to_group["A104"]

    # A101, A102, A104 must be in the same group
    assert group_of_a101 == group_of_a102
    assert group_of_a101 == group_of_a104

    # A103 must be in a separate group
    assert group_of_a103 != group_of_a101

    # Exactly 2 groups total
    assert len(clustering.groups) == 2


def test_transitive_conflict_chain_prevention():
    """
    Requirement from prompt:
    If a chain A~B~C has conflicting A and C, do not merge into one group;
    keep B with the better match and send the other to review.
    """
    samples = [
        {"id": "REC_A", "raw_address": "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"},
        {"id": "REC_B", "raw_address": "Lotus Apartments, JLN Road, Jaipur 302017"},
        {"id": "REC_C", "raw_address": "Flat 403, Lotus Apartments, JLN Road, Jaipur 302017"}
    ]
    for s in samples:
        s["normalized"] = normalize_address(s["raw_address"])
        s["components"] = extract_components(s["normalized"])

    engine = BlockingEngine()
    b_res = engine.generate_candidate_pairs(samples)

    # Use thresholds with lower auto-merge to test transitive chain handling
    thresholds = PolicyThresholds(threshold_auto=0.85, threshold_review=0.60)
    clustering = run_grouping(samples, b_res.candidate_pairs, thresholds=thresholds)

    # REC_A and REC_C MUST NOT be in the same group!
    assert clustering.record_to_group["REC_A"] != clustering.record_to_group["REC_C"]

    # Items must be sent to review queue
    assert len(clustering.review_queue) > 0
