import pytest
from backend.normalize import normalize_address
from backend.extract import extract_components, AddressComponents, ExtractedField
from backend.blocking import BlockingEngine, soundex, metaphone


def test_phonetic_keys():
    assert soundex("JLN") != ""
    assert soundex("JAIPUR") == "J160"
    assert metaphone("ROAD") == "RT"
    assert metaphone("STREET") == "STRT"


def test_candidate_generation_union():
    samples = [
        {"id": "A101", "raw_address": "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017"},
        {"id": "A102", "raw_address": "402, Lotus Apts, JLN Marg, Jaipur - 302017"},
        {"id": "A103", "raw_address": "Flat 403, Lotus Apartments, JLN Road, Jaipur 302017"},
    ]
    for s in samples:
        s["normalized"] = normalize_address(s["raw_address"])
        s["components"] = extract_components(s["normalized"])

    engine = BlockingEngine()
    result = engine.generate_candidate_pairs(samples)

    assert ("A101", "A102") in result.candidate_pairs
    assert ("A101", "A103") in result.candidate_pairs
    assert ("A102", "A103") in result.candidate_pairs


def test_oversized_block_hierarchical_sub_blocking():
    # Test block > MAX_BLOCK_SIZE (e.g. 550 records)
    records = []
    for i in range(550):
        flat = f"Flat-{100 + (i % 10)}"
        comp = AddressComponents(
            flat_no=ExtractedField(value=flat, confidence=1.0),
            building=ExtractedField(value="mega residency", confidence=0.95),
            road=ExtractedField(value="ring road", confidence=0.95),
            locality=ExtractedField(value="whitefield", confidence=0.9),
            city=ExtractedField(value="bengaluru", confidence=0.95),
            pin=ExtractedField(value="560066", confidence=0.95),
            raw_normalized=f"flat {flat} mega residency ring road whitefield bengaluru 560066"
        )
        records.append({
            "id": f"REC_{i:04d}",
            "raw_address": comp.raw_normalized,
            "normalized": comp.raw_normalized,
            "components": comp
        })

    engine = BlockingEngine(max_block_size=500)
    result = engine.generate_candidate_pairs(records)

    # Must log oversized block
    assert len(result.oversized_blocks) > 0
    logged = result.oversized_blocks[0]
    assert logged.original_size >= 550
    assert logged.sub_block_field in ["flat_no", "building", "road"]
    assert logged.sub_blocks_created > 1
