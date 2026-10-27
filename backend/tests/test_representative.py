import pytest
from backend.normalize import normalize_address
from backend.extract import extract_components
from backend.representative import select_representative


def test_select_representative_most_complete():
    samples = [
        {"id": "A101", "raw_address": "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"},
        {"id": "A102", "raw_address": "402, Lotus Apts, JLN Marg, Jaipur - 302017"},
        {"id": "A104", "raw_address": "Apt #402, Lotus Appts, Near WTP, JLN Rd, Jaipur"}
    ]
    for s in samples:
        s["normalized"] = normalize_address(s["raw_address"])
        s["components"] = extract_components(s["normalized"])

    rep = select_representative("GRP_A101", samples)

    # Must pick a real record that actually exists in the group
    assert rep.representative_record_id in ["A101", "A102", "A104"]
    assert rep.representative_address in [s["raw_address"] for s in samples]

    # Consensus components must contain real non-empty values
    assert rep.consensus_components["flat_no"] == "402"
    assert "lotus" in rep.consensus_components["building"]
    assert rep.consensus_components["city"] == "jaipur"
    assert rep.consensus_components["pin"] == "302017"
