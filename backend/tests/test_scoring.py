import pytest
from backend.normalize import normalize_address
from backend.extract import extract_components
from backend.scoring import calculate_similarity


def test_hard_conflict_different_flats():
    # Two known, different flat numbers in identical building MUST NEVER MERGE
    addr1 = "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"
    addr2 = "Flat 403, Lotus Apartments, JLN Road, Jaipur 302017"
    n1, n2 = normalize_address(addr1), normalize_address(addr2)
    c1, c2 = extract_components(n1), extract_components(n2)

    res = calculate_similarity(c1, c2, n1, n2)
    assert res.has_hard_conflict is True
    assert res.score == 0.0
    assert "HARD_CONFLICT_DIFFERENT_FLATS" in res.conflict_flags


def test_soft_penalty_pin_mismatch():
    # PIN mismatch should be a soft penalty only, not a hard conflict
    addr1 = "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"
    addr2 = "Flat 402, Lotus Apartments, JLN Road, Jaipur 302018"
    n1, n2 = normalize_address(addr1), normalize_address(addr2)
    c1, c2 = extract_components(n1), extract_components(n2)

    res = calculate_similarity(c1, c2, n1, n2)
    assert res.has_hard_conflict is False
    assert "PIN_MISMATCH_SOFT_PENALTY" in res.conflict_flags
    assert res.score >= 0.85  # Still very high match despite soft PIN penalty


def test_strong_penalty_building_mismatch():
    # Different known buildings with same flat number
    addr1 = "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"
    addr2 = "Flat 402, Sunshine Residency, JLN Road, Jaipur 302017"
    n1, n2 = normalize_address(addr1), normalize_address(addr2)
    c1, c2 = extract_components(n1), extract_components(n2)

    res = calculate_similarity(c1, c2, n1, n2)
    assert "BUILDING_MISMATCH_STRONG_PENALTY" in res.conflict_flags
    assert res.score < 0.70


def test_missing_critical_field_uncertainty():
    # Missing flat number => mark is_uncertain = True
    addr1 = "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"
    addr2 = "Lotus Apartments, JLN Road, Jaipur 302017"
    n1, n2 = normalize_address(addr1), normalize_address(addr2)
    c1, c2 = extract_components(n1), extract_components(n2)

    res = calculate_similarity(c1, c2, n1, n2)
    assert res.is_uncertain is True
    assert "MISSING_CRITICAL_FIELD_FLAT" in res.conflict_flags
