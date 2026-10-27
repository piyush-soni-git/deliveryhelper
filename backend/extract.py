"""
extract.py - Rule and Regex-based information extraction for Indian addresses.
Extracts:
- flat_no: Flat / Unit / House / Plot / Door / Room number (value + confidence)
- building: Building / Society / Apartment / Heights / Tower name (value + confidence)
- road: Road / Marg / Street / Path / Avenue (value + confidence)
- locality: Sub-area / Sector / Nagar / Colony / Landmark (value + confidence)
- city: City / Town name (value + confidence)
- pin: 6-digit Indian PIN code (value + confidence)

Missing components are strictly returned as None with 0.0 confidence (never guess).
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

INDIAN_CITIES = {
    "jaipur", "delhi", "new delhi", "mumbai", "bengaluru", "bangalore",
    "hyderabad", "chennai", "kolkata", "pune", "ahmedabad", "surat",
    "lucknow", "kanpur", "nagpur", "indore", "bhopal", "visakhapatnam",
    "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik",
    "faridabad", "meerut", "rajkot", "varanasi", "srinagar", "aurangabad",
    "dhanbad", "amritsar", "navi mumbai", "allahabad", "prayagraj", "ranchi",
    "howrah", "coimbatore", "jabalpur", "gwalior", "vijayawada", "jodhpur",
    "madurai", "raipur", "kota", "guwahati", "chandigarh", "solapur",
    "hubballi", "bareilly", "moradabad", "mysuru", "gurugram", "gurgaon",
    "aligarh", "jalandhar", "tiruchirappalli", "bhubaneswar", "salem",
    "mira bhayandar", "thiruvananthapuram", "bhiwandi", "saharanpur", "gorakhpur",
    "guntur", "bikaner", "amravati", "noida", "greater noida", "jamshedpur",
    "bhilai", "cuttack", "firozabad", "kochi", "nellore", "bhavnagar",
    "dehradun", "durgapur", "asansol", "rourkela", "nanded", "kolhapur",
    "ajmer", "akola", "gulbarga", "jamnagar", "ujjain", "loni", "siliguri",
    "jhansi", "ulhasnagar", "jammu", "sangli", "mangalore", "erode", "belagavi",
    "kurnool", "ambattur", "rajahmundry", "tirunelveli", "malegaon", "gaya",
    "tiruppur", "davanagere", "kozhikode", "bokaro", "bellary", "patiala",
    "rohtak", "panipat", "shimla", "udaipur", "gandhinagar", "secunderabad"
}

BUILDING_SUFFIX_KEYWORDS = {
    "apartments", "apartment", "residency", "heights", "height", "towers", "tower",
    "enclave", "society", "complex", "villas", "villa", "court", "palace", "manor",
    "bhavan", "bhawan", "chambers", "arcade", "plaza", "greens", "regency", "view",
    "estate", "castle", "nest", "paradise", "parkview", "residence", "niketan"
}

ROAD_KEYWORDS = {
    "road", "marg", "street", "lane", "path", "avenue", "boulevard", "highway",
    "bypass", "cross", "way", "drive"
}

LANDMARK_PREFIXES = {"near", "opposite", "behind", "adjacent"}

STOP_WORDS = {
    "flat", "unit", "house", "plot", "door", "room", "floor", "no", "num", "number",
    "near", "opposite", "behind", "adjacent", "in", "at", "to", "the", "of", "and"
}


@dataclass
class ExtractedField:
    value: Optional[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "confidence": round(self.confidence, 2)}


@dataclass
class AddressComponents:
    flat_no: ExtractedField
    building: ExtractedField
    road: ExtractedField
    locality: ExtractedField
    city: ExtractedField
    pin: ExtractedField
    raw_normalized: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flat_no": self.flat_no.to_dict(),
            "building": self.building.to_dict(),
            "road": self.road.to_dict(),
            "locality": self.locality.to_dict(),
            "city": self.city.to_dict(),
            "pin": self.pin.to_dict(),
            "raw_normalized": self.raw_normalized,
        }

    def has_critical_fields(self) -> bool:
        has_flat = self.flat_no.value is not None
        has_location = (self.building.value is not None or 
                        self.locality.value is not None or 
                        self.road.value is not None)
        return has_flat and has_location


def extract_pin(text: str) -> ExtractedField:
    matches = list(re.finditer(r'\b([1-9][0-9]{5})\b', text))
    if not matches:
        return ExtractedField(value=None, confidence=0.0)
    
    for match in matches:
        start_idx = match.start()
        prefix = text[max(0, start_idx - 15):start_idx]
        if re.search(r'\b(pin|pincode|code)\b', prefix):
            return ExtractedField(value=match.group(1), confidence=1.0)
            
    pin_val = matches[-1].group(1)
    return ExtractedField(value=pin_val, confidence=0.95)


def extract_flat_no(text: str) -> ExtractedField:
    # 1. Explicit flat / unit / house / room / plot / door prefix
    pattern_explicit = (
        r'\b(?:flat|unit|house|plot|door|room|villa|f|apartments?\s+no)\s*(?:no|num|number)?\s*'
        r'[:#-]?\s*([a-z0-9]+(?:[-/][a-z0-9]+)?)\b'
    )
    match = re.search(pattern_explicit, text)
    if match:
        val = match.group(1).strip()
        if val and not (len(val) == 6 and val.isdigit() and val[0] in "123456789"):
            return ExtractedField(value=val, confidence=1.0)
            
    # 2. Match pattern like 'no 402' or 'no a-101'
    pattern_hash_no = r'\b(?:no)\s+([a-z0-9]+(?:[-/][a-z0-9]+)?)\b'
    match_no = re.search(pattern_hash_no, text)
    if match_no:
        val = match_no.group(1).strip()
        if not (len(val) == 6 and val.isdigit()):
            return ExtractedField(value=val, confidence=0.95)

    # 3. Match leading unit identifier at beginning of address followed by text
    pattern_leading = r'^([a-z]?-?[0-9]{1,4}[a-z]?(?:[-/][a-z0-9]+)?)\s+(?=[a-z])'
    match_leading = re.search(pattern_leading, text)
    if match_leading:
        val = match_leading.group(1).strip()
        if not (len(val) == 6 and val.isdigit()):
            return ExtractedField(value=val, confidence=0.85)

    return ExtractedField(value=None, confidence=0.0)


def extract_building(text: str) -> ExtractedField:
    tokens = text.split()
    for i, token in enumerate(tokens):
        if token in BUILDING_SUFFIX_KEYWORDS:
            # Look backwards up to 3 tokens, stopping at unit/digits or stop words
            filtered: List[str] = []
            for idx in range(i - 1, max(-1, i - 4), -1):
                t = tokens[idx]
                # If token contains digits or is a unit indicator, stop backwards scan
                if any(c.isdigit() for c in t) or t in {"unit", "flat", "house", "plot", "no"}:
                    break
                if t in STOP_WORDS or t in ROAD_KEYWORDS:
                    break
                filtered.insert(0, t)

            if filtered:
                building_name = " ".join(filtered[-2:] + [token])
                return ExtractedField(value=building_name, confidence=0.95)
            elif i > 0 and tokens[i-1] not in STOP_WORDS and not any(c.isdigit() for c in tokens[i-1]):
                return ExtractedField(value=f"{tokens[i-1]} {token}", confidence=0.90)

    return ExtractedField(value=None, confidence=0.0)


def extract_road(text: str) -> ExtractedField:
    tokens = text.split()
    for i, token in enumerate(tokens):
        if token in ROAD_KEYWORDS:
            # Look backwards up to 3 tokens, stopping at building suffixes or landmark prefixes
            filtered: List[str] = []
            for idx in range(i - 1, max(-1, i - 4), -1):
                t = tokens[idx]
                if t in BUILDING_SUFFIX_KEYWORDS or t in LANDMARK_PREFIXES:
                    break
                if idx > 0 and tokens[idx - 1] in LANDMARK_PREFIXES:
                    # Token was preceded by landmark prefix e.g. 'near wtp'
                    break
                if any(c.isdigit() for c in t) or t in STOP_WORDS:
                    break
                filtered.insert(0, t)

            if filtered:
                road_name = " ".join(filtered[-2:] + [token])
                return ExtractedField(value=road_name, confidence=0.95)

    return ExtractedField(value=None, confidence=0.0)


def extract_locality(text: str) -> ExtractedField:
    # 1. Landmark pattern: near/opposite/behind + target word
    pattern_landmark = r'\b(near|opposite|behind|adjacent)\s+([a-z0-9]+)\b'
    match_lm = re.search(pattern_landmark, text)
    if match_lm:
        rel = match_lm.group(1)
        raw_target = match_lm.group(2).strip()
        if raw_target not in ROAD_KEYWORDS and raw_target not in BUILDING_SUFFIX_KEYWORDS and raw_target not in INDIAN_CITIES:
            return ExtractedField(value=f"{rel} {raw_target}", confidence=0.90)

    # 2. Sector / Phase patterns: 'sector 14', 'phase 2'
    pattern_sec = r'\b(sector|phase|sec|ph)\s*([0-9]{1,3}[a-z]?)\b'
    match_sec = re.search(pattern_sec, text)
    if match_sec:
        return ExtractedField(value=f"{match_sec.group(1)} {match_sec.group(2)}", confidence=0.95)

    # 3. Locality suffix patterns: '<name> nagar', '<name> colony', '<name> vihar'
    tokens = text.split()
    loc_suffixes = {"nagar", "colony", "vihar", "puram", "layout", "enclave", "basti", "chowk"}
    for i, token in enumerate(tokens):
        if token in loc_suffixes and i > 0:
            prefix = tokens[i-1]
            if prefix not in STOP_WORDS and prefix not in BUILDING_SUFFIX_KEYWORDS and not any(c.isdigit() for c in prefix):
                return ExtractedField(value=f"{prefix} {token}", confidence=0.90)

    return ExtractedField(value=None, confidence=0.0)


def extract_city(text: str) -> ExtractedField:
    for city in sorted(INDIAN_CITIES, key=lambda c: len(c.split()), reverse=True):
        pattern = rf'\b{re.escape(city)}\b'
        if re.search(pattern, text):
            return ExtractedField(value=city, confidence=0.95)
            
    return ExtractedField(value=None, confidence=0.0)


def extract_components(normalized_text: str) -> AddressComponents:
    if not normalized_text:
        empty = ExtractedField(value=None, confidence=0.0)
        return AddressComponents(
            flat_no=empty,
            building=empty,
            road=empty,
            locality=empty,
            city=empty,
            pin=empty,
            raw_normalized=""
        )

    pin = extract_pin(normalized_text)
    flat_no = extract_flat_no(normalized_text)
    building = extract_building(normalized_text)
    road = extract_road(normalized_text)
    locality = extract_locality(normalized_text)
    city = extract_city(normalized_text)

    return AddressComponents(
        flat_no=flat_no,
        building=building,
        road=road,
        locality=locality,
        city=city,
        pin=pin,
        raw_normalized=normalized_text
    )
