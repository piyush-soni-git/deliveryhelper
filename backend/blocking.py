"""
blocking.py - Scalable Candidate Generation and Blocking Engine.
Generates candidate pairs using multiple blocking keys:
(a) Building + locality tokens
(b) Soundex / Metaphone of road name + city
(c) MinHash LSH on character 3-grams of normalized text

Implements MAX_BLOCK_SIZE (default 500) with hierarchical sub-blocking:
Oversized blocks (>500) are hierarchically sub-blocked by:
1. flat_no
2. building
3. road
Every oversized block event is formally logged.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional, Any
from datasketch import MinHash, MinHashLSH

from backend.extract import AddressComponents

logger = logging.getLogger(__name__)


def soundex(token: str) -> str:
    """Computes standard Soundex code for a token."""
    if not token or not token.strip():
        return "0000"
    clean = "".join(c.upper() for c in token if c.isalpha())
    if not clean:
        return "0000"
    first = clean[0]
    mapping = {
        'BFPV': '1',
        'CGJKQSXZ': '2',
        'DT': '3',
        'L': '4',
        'MN': '5',
        'R': '6'
    }
    code = [first]
    for char in clean[1:]:
        for keys, digit in mapping.items():
            if char in keys:
                if digit != code[-1]:
                    code.append(digit)
                break
    return "".join(code)[:4].ljust(4, '0')


def metaphone(token: str) -> str:
    """
    Computes a simplified Metaphone phonetic representation for English/Indian romanized words.
    """
    if not token or not token.strip():
        return ""
    w = token.upper().strip()
    # Basic phonetic transformation rules
    w = w.replace("PH", "F").replace("GH", "G").replace("TH", "T")
    w = w.replace("CK", "K").replace("SH", "X").replace("CH", "X")
    w = w.replace("DG", "J").replace("WR", "R").replace("KN", "N")
    w = w.replace("D", "T")
    
    res = []
    vowels = {'A', 'E', 'I', 'O', 'U', 'Y'}
    for i, ch in enumerate(w):
        if i == 0 and ch in vowels:
            res.append(ch)
        elif ch not in vowels:
            if not res or res[-1] != ch:
                res.append(ch)
                
    return "".join(res)[:6]


def get_char_3grams(text: str) -> Set[str]:
    """Extract character 3-grams from normalized text."""
    if not text:
        return set()
    cleaned = f"  {text}  "
    return {cleaned[i:i+3] for i in range(len(cleaned) - 2)}


@dataclass
class OversizedBlockRecord:
    key: str
    original_size: int
    sub_block_field: str
    sub_blocks_created: int


@dataclass
class BlockingResult:
    candidate_pairs: Set[Tuple[str, str]]
    oversized_blocks: List[OversizedBlockRecord]
    block_sizes: Dict[str, int]
    total_comparisons_generated: int
    naive_comparisons: int
    reduction_ratio: float


class BlockingEngine:
    def __init__(self, max_block_size: int = 500, lsh_threshold: float = 0.5, num_perm: int = 64):
        self.max_block_size = max_block_size
        self.lsh_threshold = lsh_threshold
        self.num_perm = num_perm
        self.oversized_logs: List[OversizedBlockRecord] = []

    def _hierarchical_sub_block(
        self,
        block_records: List[Dict[str, Any]],
        current_key: str
    ) -> List[List[Dict[str, Any]]]:
        """
        Hierarchically sub-blocks an oversized block (> MAX_BLOCK_SIZE):
        1. Sub-block by flat_no
        2. If any sub-group still > MAX_BLOCK_SIZE, sub-block by building
        3. If still > MAX_BLOCK_SIZE, sub-block by road
        """
        result_sub_blocks: List[List[Dict[str, Any]]] = []

        # Tier 1: Sub-block by flat_no
        flat_groups = defaultdict(list)
        for r in block_records:
            comp: AddressComponents = r["components"]
            fn = comp.flat_no.value or "no_flat"
            flat_groups[fn].append(r)

        self.oversized_logs.append(OversizedBlockRecord(
            key=current_key,
            original_size=len(block_records),
            sub_block_field="flat_no",
            sub_blocks_created=len(flat_groups)
        ))

        for flat_key, f_records in flat_groups.items():
            if len(f_records) <= self.max_block_size:
                result_sub_blocks.append(f_records)
            else:
                # Tier 2: Sub-block by building
                bldg_groups = defaultdict(list)
                for r in f_records:
                    comp: AddressComponents = r["components"]
                    bldg = comp.building.value or "no_bldg"
                    bldg_groups[bldg].append(r)

                self.oversized_logs.append(OversizedBlockRecord(
                    key=f"{current_key}|flat:{flat_key}",
                    original_size=len(f_records),
                    sub_block_field="building",
                    sub_blocks_created=len(bldg_groups)
                ))

                for bldg_key, b_records in bldg_groups.items():
                    if len(b_records) <= self.max_block_size:
                        result_sub_blocks.append(b_records)
                    else:
                        # Tier 3: Sub-block by road
                        road_groups = defaultdict(list)
                        for r in b_records:
                            comp: AddressComponents = r["components"]
                            road = comp.road.value or "no_road"
                            road_groups[road].append(r)

                        self.oversized_logs.append(OversizedBlockRecord(
                            key=f"{current_key}|flat:{flat_key}|bldg:{bldg_key}",
                            original_size=len(b_records),
                            sub_block_field="road",
                            sub_blocks_created=len(road_groups)
                        ))

                        for _, r_records in road_groups.items():
                            # If leaf block still exceeds max_block_size, cap it to prevent combinatorial explosion
                            result_sub_blocks.append(r_records[:self.max_block_size])

        return result_sub_blocks

    def generate_candidate_pairs(self, records: List[Dict[str, Any]]) -> BlockingResult:
        """
        Executes multi-key blocking with LSH and hierarchical sub-blocking.
        Each record dict must have:
        - 'id': str
        - 'raw_address': str
        - 'normalized': str
        - 'components': AddressComponents
        """
        n = len(records)
        naive_pairs = (n * (n - 1)) // 2 if n > 1 else 0
        self.oversized_logs = []
        
        candidates: Set[Tuple[str, str]] = set()
        block_sizes: Dict[str, int] = {}

        # -------------------------------------------------------------
        # Key A: Building + Locality (or City) tokens
        # -------------------------------------------------------------
        blocks_a = defaultdict(list)
        for r in records:
            comp: AddressComponents = r["components"]
            bldg = comp.building.value or ""
            loc = comp.locality.value or ""
            city = comp.city.value or ""
            pin = comp.pin.value or ""

            if bldg and (loc or city):
                key = f"A|bldg:{bldg}|loc:{loc or city}"
            elif bldg:
                key = f"A|bldg:{bldg}|pin:{pin or city}"
            elif loc and city:
                key = f"A|loc:{loc}|city:{city}"
            elif pin:
                key = f"A|pin:{pin}"
            else:
                key = f"A|city:{city or 'unknown'}"
            blocks_a[key].append(r)

        # -------------------------------------------------------------
        # Key B: Soundex / Metaphone of Road + City
        # -------------------------------------------------------------
        blocks_b = defaultdict(list)
        for r in records:
            comp: AddressComponents = r["components"]
            road = comp.road.value or ""
            city = comp.city.value or ""

            if road and city:
                road_phon = metaphone(road)
                city_phon = soundex(city)
                key = f"B|road_phon:{road_phon}|city_phon:{city_phon}"
                blocks_b[key].append(r)
            elif road:
                key = f"B|road_phon:{metaphone(road)}"
                blocks_b[key].append(r)

        # Process Key A and B blocks with hierarchical sub-blocking
        all_blocks = {**blocks_a, **blocks_b}
        for b_key, b_records in all_blocks.items():
            count = len(b_records)
            block_sizes[b_key] = count
            
            if count <= 1:
                continue

            if count > self.max_block_size:
                sub_blocks = self._hierarchical_sub_block(b_records, b_key)
                for sub_b in sub_blocks:
                    sub_len = len(sub_b)
                    for i in range(sub_len):
                        id1 = sub_b[i]["id"]
                        for j in range(i + 1, sub_len):
                            id2 = sub_b[j]["id"]
                            pair = (min(id1, id2), max(id1, id2))
                            candidates.add(pair)
            else:
                for i in range(count):
                    id1 = b_records[i]["id"]
                    for j in range(i + 1, count):
                        id2 = b_records[j]["id"]
                        pair = (min(id1, id2), max(id1, id2))
                        candidates.add(pair)

        # -------------------------------------------------------------
        # Key C: MinHash LSH on Character 3-Grams of Normalized Text
        # -------------------------------------------------------------
        if n > 1:
            try:
                lsh = MinHashLSH(threshold=self.lsh_threshold, num_perm=self.num_perm)
                minhashes = {}
                for r in records:
                    rec_id = r["id"]
                    norm_text = r["normalized"]
                    m = MinHash(num_perm=self.num_perm)
                    grams = get_char_3grams(norm_text)
                    for g in grams:
                        m.update(g.encode('utf-8'))
                    minhashes[rec_id] = m
                    lsh.insert(rec_id, m)

                for rec_id, m in minhashes.items():
                    similar_ids = lsh.query(m)
                    for other_id in similar_ids:
                        if other_id != rec_id:
                            pair = (min(rec_id, other_id), max(rec_id, other_id))
                            candidates.add(pair)
            except Exception as e:
                logger.warning(f"MinHash LSH execution notice: {e}")

        total_cand = len(candidates)
        reduction = 1.0 - (total_cand / naive_pairs) if naive_pairs > 0 else 0.0

        return BlockingResult(
            candidate_pairs=candidates,
            oversized_blocks=self.oversized_logs,
            block_sizes=block_sizes,
            total_comparisons_generated=total_cand,
            naive_comparisons=naive_pairs,
            reduction_ratio=round(reduction, 4)
        )
