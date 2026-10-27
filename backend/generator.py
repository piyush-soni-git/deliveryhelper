"""
generator.py - Synthetic Indian Address Generator with Hard Negatives and Ground Truth.

Features:
- Produces realistic Indian addresses across Hindi and English scripts.
- Realistic perturbations: abbreviations, typos, component reordering, missing/perturbed PINs.
- HARD NEGATIVES: Multiple distinct flats/units residing inside the exact same building/society.
- Embedded canonical benchmark set A101-A104 (Lotus Apartments, JLN Road, Jaipur).
- Full ground-truth labels for precision, recall, and false-merge evaluation.
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

# Reference benchmark dataset required by prompt
REFERENCE_A101_A104: List[Dict[str, Any]] = [
    {
        "id": "A101",
        "raw_address": "Flat 402, Lotus Apartments, JLN Road, Jaipur 302017",
        "ground_truth_group": "GT_LOTUS_402",
        "flat": "402",
        "building": "Lotus Apartments",
        "road": "JLN Road",
        "locality": None,
        "city": "Jaipur",
        "pin": "302017"
    },
    {
        "id": "A102",
        "raw_address": "402, Lotus Apts, JLN Marg, Jaipur - 302017",
        "ground_truth_group": "GT_LOTUS_402",
        "flat": "402",
        "building": "Lotus Apartments",
        "road": "JLN Road",
        "locality": None,
        "city": "Jaipur",
        "pin": "302017"
    },
    {
        "id": "A103",
        "raw_address": "Flat 403, Lotus Apartments, JLN Road, Jaipur 302017",
        "ground_truth_group": "GT_LOTUS_403",
        "flat": "403",
        "building": "Lotus Apartments",
        "road": "JLN Road",
        "locality": None,
        "city": "Jaipur",
        "pin": "302017"
    },
    {
        "id": "A104",
        "raw_address": "Apt #402, Lotus Appts, Near WTP, JLN Rd, Jaipur",
        "ground_truth_group": "GT_LOTUS_402",
        "flat": "402",
        "building": "Lotus Apartments",
        "road": "JLN Road",
        "locality": "Near WTP",
        "city": "Jaipur",
        "pin": None
    }
]

INDIAN_CITIES_DATA = [
    ("Jaipur", "302017", ["JLN Marg", "Tonk Road", "Ajmer Road", "MI Road", "Sirsi Road"], ["Malviya Nagar", "Mansarovar", "Vaishali Nagar", "C Scheme", "Near WTP"]),
    ("Bengaluru", "560038", ["100 Feet Road", "Outer Ring Road", "Hosur Road", "Bannerghatta Road", "MG Road"], ["Indiranagar", "Koramangala", "Whitefield", "HSR Layout", "Jayanagar"]),
    ("Mumbai", "400053", ["Linking Road", "SV Road", "Western Express Highway", "LBS Marg", "Hill Road"], ["Andheri West", "Bandra West", "Powai", "Borivali East", "Juhu"]),
    ("Delhi", "110016", ["Ring Road", "Aurobindo Marg", "Vikas Marg", "Barakhamba Road", "Outer Ring Road"], ["Hauz Khas", "Connaught Place", "Dwarka Sector 12", "Rohini Sector 7", "Saket"]),
    ("Pune", "411004", ["FC Road", "JM Road", "Karve Road", "Senapati Bapat Road", "Baner Road"], ["Shivajinagar", "Kothrud", "Viman Nagar", "Hinjawadi Phase 1", "Aundh"]),
    ("Hyderabad", "500081", ["Hitec City Main Road", "Gachibowli Road", "Banjara Hills Road No 1", "Jubilee Hills Road 36", "Inner Ring Road"], ["Madhapur", "Gachibowli", "Kondapur", "Banjara Hills", "Kukatpally"]),
]

BUILDING_NAMES = [
    "Lotus Apartments", "Galaxy Heights", "Prestige Towers", "Shanti Niketan",
    "Silver Oak Residency", "Green Valley Society", "Royal Palms Enclave", "Sunshine Complex",
    "Emerald Court", "Sylvan View", "Palm Meadows", "Sapphire Heights",
    "Godrej Woods", "Sobha Dream Acres", "Brigade Metropolis", "Hiranandani Gardens"
]

HINDI_BUILDING_MAP = {
    "Lotus Apartments": "कमल अपार्टमेंट",
    "Galaxy Heights": "गैलेक्सी हाइट्स",
    "Prestige Towers": "प्रेस्टीज टावर्स",
    "Shanti Niketan": "शान्ति निकेतन",
    "Silver Oak Residency": "सिल्वर ओक रेजिडेंसी",
    "Green Valley Society": "ग्रीन वैली सोसायटी"
}

HINDI_ROAD_MAP = {
    "JLN Road": "जेएलएन मार्ग",
    "Tonk Road": "टोंक रोड",
    "Ajmer Road": "अजमेर रोड",
    "MG Road": "एमजी रोड",
    "Ring Road": "रिंग रोड",
    "Outer Ring Road": "आउटर रिंग रोड"
}

HINDI_CITY_MAP = {
    "Jaipur": "जयपुर",
    "Bengaluru": "बेंगलुरु",
    "Mumbai": "मुंबई",
    "Delhi": "दिल्ली",
    "Pune": "पुणे",
    "Hyderabad": "हैदराबाद"
}


def introduce_typo(text: str) -> str:
    """Randomly introduces realistic OCR / typographical error."""
    if len(text) < 4 or random.random() > 0.35:
        return text
    idx = random.randint(1, len(text) - 2)
    op = random.choice(["swap", "delete", "repeat"])
    if op == "swap":
        return text[:idx] + text[idx+1] + text[idx] + text[idx+2:]
    elif op == "delete":
        return text[:idx] + text[idx+1:]
    elif op == "repeat":
        return text[:idx] + text[idx] + text[idx] + text[idx+1:]
    return text


def format_address_variant(
    flat_no: str,
    building: str,
    road: str,
    locality: Optional[str],
    city: str,
    pin: Optional[str],
    variant_idx: int,
    use_hindi: bool = False
) -> str:
    """Constructs a randomized, realistic variation of a physical address."""
    if use_hindi and building in HINDI_BUILDING_MAP:
        h_bldg = HINDI_BUILDING_MAP[building]
        h_road = HINDI_ROAD_MAP.get(road, road)
        h_city = HINDI_CITY_MAP.get(city, city)
        h_flat_prefix = random.choice(["फ्लैट नं", "फ्लैट", "मकान नं", "कमरा नं"])
        parts = [f"{h_flat_prefix} {flat_no}", h_bldg, h_road, h_city]
        if pin and random.random() > 0.2:
            parts.append(str(pin))
        return ", ".join(parts)

    # English variations
    flat_prefixes = ["Flat", "Flat No.", "Apt", "Unit", "#", "F-", "Flat-", ""]
    flat_str = f"{random.choice(flat_prefixes)} {flat_no}".strip() if random.random() > 0.1 else flat_no

    bldg_str = building
    if "Apartments" in bldg_str:
        bldg_str = bldg_str.replace("Apartments", random.choice(["Apts", "Apt.", "Apartment", "Appts", "Apartments"]))
    elif "Residency" in bldg_str:
        bldg_str = bldg_str.replace("Residency", random.choice(["Res.", "Residency", "Residencies"]))
    elif "Society" in bldg_str:
        bldg_str = bldg_str.replace("Society", random.choice(["Soc.", "Society", "Socty"]))

    road_str = road
    if "Road" in road_str:
        road_str = road_str.replace("Road", random.choice(["Rd", "Rd.", "Marg", "Road"]))

    bldg_str = introduce_typo(bldg_str)
    road_str = introduce_typo(road_str)

    # PIN variation: 80% correct, 10% omitted, 10% typo PIN
    pin_str = pin
    r_pin = random.random()
    if r_pin < 0.10:
        pin_str = None
    elif r_pin < 0.18 and pin:
        pin_int = int(pin)
        pin_str = str(pin_int + random.choice([-1, 1, 10, -10]))

    # Component ordering
    order_type = random.choice(["standard", "reordered_city_first", "landmark_front"])
    components = []

    if order_type == "reordered_city_first":
        components = [city, road_str, flat_str, bldg_str]
        if locality and random.random() > 0.3:
            components.append(locality)
        if pin_str:
            components.append(pin_str)
    elif order_type == "landmark_front" and locality:
        components = [locality, flat_str, bldg_str, road_str, city]
        if pin_str:
            components.append(pin_str)
    else:
        # Standard
        components = [flat_str, bldg_str]
        if locality and random.random() > 0.4:
            components.append(locality)
        components.extend([road_str, city])
        if pin_str:
            components.append(pin_str)

    sep = random.choice([", ", " - ", ", ", " "])
    return sep.join(filter(None, components))


def generate_synthetic_dataset(
    num_records: int = 1000,
    seed: int = 42,
    include_canonical_reference: bool = True
) -> List[Dict[str, Any]]:
    """
    Generates synthetic Indian address records with ground truth delivery points.
    Includes HARD NEGATIVES (different flats in the same building).
    """
    random.seed(seed)
    records: List[Dict[str, Any]] = []

    if include_canonical_reference:
        records.extend(REFERENCE_A101_A104)

    target_count = num_records
    current_rec_num = len(records) + 1

    # Average 2.5 records per physical delivery point
    num_delivery_points = max(5, int((target_count - len(records)) / 2.5))

    # Pre-generate delivery points, grouped into buildings (Hard Negatives!)
    dp_list = []
    dp_counter = 1

    for _ in range(num_delivery_points):
        city_info = random.choice(INDIAN_CITIES_DATA)
        city_name, base_pin, roads, localities = city_info
        building = random.choice(BUILDING_NAMES)
        road = random.choice(roads)
        locality = random.choice(localities) if random.random() > 0.3 else None

        # Generate multiple distinct flats in this building (HARD NEGATIVES)
        num_flats_in_building = random.randint(1, 4)
        for _ in range(num_flats_in_building):
            floor = random.randint(1, 15)
            door = random.randint(1, 6)
            flat_no = f"{floor*100 + door}"
            if random.random() > 0.8:
                flat_no = f"{random.choice(['A', 'B', 'C'])}-{flat_no}"

            dp_id = f"DP_{dp_counter:06d}"
            dp_counter += 1
            dp_list.append({
                "dp_id": dp_id,
                "flat_no": flat_no,
                "building": building,
                "road": road,
                "locality": locality,
                "city": city_name,
                "pin": base_pin
            })

    # Generate variants for each delivery point
    dp_idx = 0
    while len(records) < target_count:
        dp = dp_list[dp_idx % len(dp_list)]
        dp_idx += 1

        # Generate 1 to 4 variant addresses for this delivery point
        num_variants = random.randint(1, 3)
        for v in range(num_variants):
            if len(records) >= target_count:
                break
            rec_id = f"REC_{current_rec_num:06d}"
            current_rec_num += 1

            use_hindi = (random.random() < 0.15)
            raw_addr = format_address_variant(
                flat_no=dp["flat_no"],
                building=dp["building"],
                road=dp["road"],
                locality=dp["locality"],
                city=dp["city"],
                pin=dp["pin"],
                variant_idx=v,
                use_hindi=use_hindi
            )

            records.append({
                "id": rec_id,
                "raw_address": raw_addr,
                "ground_truth_group": dp["dp_id"],
                "flat": dp["flat_no"],
                "building": dp["building"],
                "road": dp["road"],
                "locality": dp["locality"],
                "city": dp["city"],
                "pin": dp["pin"]
            })

    return records
