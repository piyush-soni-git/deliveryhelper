import pytest
from backend.normalize import normalize_address
from backend.extract import extract_components


def test_extract_canonical_a101():
    addr = "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"
    norm = normalize_address(addr)
    comp = extract_components(norm)

    assert comp.flat_no.value == "402"
    assert comp.flat_no.confidence >= 0.85
    assert comp.building.value == "lotus apartments"
    assert comp.road.value == "jln road"
    assert comp.city.value == "jaipur"
    assert comp.pin.value == "302017"


def test_extract_missing_fields_return_none():
    # Never guess missing fields
    addr = "Lotus Apartments, Jaipur"
    norm = normalize_address(addr)
    comp = extract_components(norm)

    assert comp.flat_no.value is None
    assert comp.flat_no.confidence == 0.0
    assert comp.road.value is None
    assert comp.pin.value is None
    assert comp.building.value == "lotus apartments"
    assert comp.city.value == "jaipur"


def test_extract_hyphenated_flat_and_landmark():
    addr = "Unit A-101, Galaxy Residency, Near WTP, Malviya Nagar, Jaipur 302017"
    norm = normalize_address(addr)
    comp = extract_components(norm)

    assert comp.flat_no.value == "a-101"
    assert comp.building.value == "galaxy residency"
    assert comp.locality.value == "near wtp"
    assert comp.city.value == "jaipur"
    assert comp.pin.value == "302017"


def test_extract_leading_flat_number():
    addr = "402 Lotus Apts JLN Marg Jaipur 302017"
    norm = normalize_address(addr)
    comp = extract_components(norm)

    assert comp.flat_no.value == "402"
    assert comp.building.value == "lotus apartments"
    assert comp.city.value == "jaipur"
