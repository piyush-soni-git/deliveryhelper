import pytest
from backend.normalize import (
    normalize_address,
    transliterate_devanagari,
    convert_devanagari_digits,
    clean_punctuation,
    expand_abbreviations
)


def test_lowercase_and_whitespace():
    raw = "  Flat   402,   LOTUS APTS,  Jaipur   "
    norm = normalize_address(raw)
    assert norm == "flat 402 lotus apartments jaipur"


def test_devanagari_numerals_preservation():
    # Devanagari numerals ३०२०१७ should convert to standard digits 302017
    hindi_pin = "जयपुर ३०२०१७"
    norm = normalize_address(hindi_pin)
    assert "302017" in norm
    assert "jaipur" in norm


def test_hindi_lexicon_transliteration():
    raw = "फ्लैट नं 402, कमल अपार्टमेंट, जेएलएन मार्ग, जयपुर ३०२०१७"
    norm = normalize_address(raw)
    assert "flat" in norm
    assert "402" in norm
    assert "lotus apartments" in norm
    assert "road" in norm
    assert "jaipur" in norm
    assert "302017" in norm


def test_abbreviation_expansion():
    raw = "Apt 12, MG Rd, Nr WTP, Extn 2, Soc 4, Blk B"
    norm = normalize_address(raw)
    assert "apartments 12" in norm
    assert "road" in norm
    assert "near" in norm
    assert "extension 2" in norm
    assert "society 4" in norm
    assert "block b" in norm


def test_numbers_never_altered():
    # Critical requirement: NEVER alter numbers
    test_cases = [
        ("Flat 402/B", "402/b"),
        ("Plot No 104-A", "104-a"),
        ("Tower 3, Unit 501", "501"),
        ("PIN 302017", "302017")
    ]
    for raw, expected_token in test_cases:
        norm = normalize_address(raw)
        assert expected_token in norm
