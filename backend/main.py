"""
main.py - FastAPI Web Service for AddressMatch.
Provides REST APIs for:
1. Playground: Interactive two-address comparison and explanation
2. Batch Run: Deduplication pipeline over synthetic or uploaded CSV data
3. Review Queue: Human-in-the-loop review with feedback loop to clustering
4. Metrics Dashboard: Ground-truth evaluation, false-merge rates, block-size histograms
5. Scalability Engine: Benchmark curves vs naive O(N^2) complexity
6. Dynamic Configuration: Live threshold updates
"""

import io
import csv
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.normalize import normalize_address
from backend.extract import extract_components, AddressComponents
from backend.blocking import BlockingEngine
from backend.scoring import calculate_similarity, MatchScoreResult
from backend.policy import Tier, PolicyThresholds, evaluate_tier
from backend.grouping import run_grouping, ClusteringResult, ReviewQueueItem, ConsistencyUnionFind
from backend.representative import select_representative, GroupRepresentation
from backend.generator import generate_synthetic_dataset, REFERENCE_A101_A104
from backend.benchmark import get_scalability_series, SCALABILITY_ANALYSIS_TEXT

app = FastAPI(
    title="AddressMatch API",
    description="Scalable Indian Address Entity Resolution & Deduplication Service",
    version="1.0.0"
)

# Enable CORS for React frontend (Vite default: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory state for the active batch run and review queue
class AppState:
    def __init__(self):
        self.thresholds = PolicyThresholds(threshold_auto=0.90, threshold_review=0.70)
        self.current_records: Dict[str, Dict[str, Any]] = {}
        self.current_clustering: Optional[ClusteringResult] = None
        self.current_groups: Dict[str, GroupRepresentation] = {}
        self.review_queue: List[ReviewQueueItem] = []
        self.latest_metrics: Dict[str, Any] = {}
        self.blocking_summary: Dict[str, Any] = {}
        self.union_find: Optional[ConsistencyUnionFind] = None

state = AppState()


# =====================================================================
# Request / Response Models
# =====================================================================

class PlaygroundRequest(BaseModel):
    address1: str = Field(..., example="Flat 402, Lotus Apartments, JLN Road, Jaipur 302017")
    address2: str = Field(..., example="402, Lotus Apts, JLN Marg, Jaipur - 302017")
    threshold_auto: Optional[float] = None
    threshold_review: Optional[float] = None


class ThresholdConfigRequest(BaseModel):
    threshold_auto: float = Field(..., ge=0.5, le=1.0)
    threshold_review: float = Field(..., ge=0.3, le=0.95)


class ReviewDecisionRequest(BaseModel):
    id1: str
    id2: str
    decision: str = Field(..., pattern="^(APPROVE|REJECT)$")


class BatchRunRequest(BaseModel):
    source: str = Field("sample", description="'canonical', 'synthetic', or 'uploaded'")
    num_records: int = Field(500, ge=4, le=10000)
    max_block_size: int = Field(500, ge=10, le=2000)
    seed: int = Field(42)


# =====================================================================
# Pipeline Helpers
# =====================================================================

def compute_metrics(records: Dict[str, Dict[str, Any]], record_to_group: Dict[str, str]) -> Dict[str, Any]:
    """Calculates ground truth metrics if labels are present."""
    # Check if records have ground_truth_group
    labeled = [r for r in records.values() if r.get("ground_truth_group")]
    if len(labeled) < 2:
        return {"has_ground_truth": False}

    # Evaluate all pairs among labeled records (sample up to 2000 records to keep evaluation fast)
    eval_records = labeled[:1500]
    n = len(eval_records)
    tp = fp = fn = tn = 0
    incomplete_correct = 0
    incomplete_total = 0

    for i in range(n):
        r1 = eval_records[i]
        id1 = r1["id"]
        gt1 = r1["ground_truth_group"]
        pred1 = record_to_group.get(id1)
        comp1: AddressComponents = r1["components"]
        is_inc1 = (comp1.flat_no.value is None or comp1.pin.value is None or comp1.building.value is None)

        for j in range(i + 1, n):
            r2 = eval_records[j]
            id2 = r2["id"]
            gt2 = r2["ground_truth_group"]
            pred2 = record_to_group.get(id2)

            is_true_match = (gt1 == gt2)
            is_pred_match = (pred1 == pred2)

            if is_true_match and is_pred_match:
                tp += 1
            elif not is_true_match and is_pred_match:
                fp += 1  # False merge!
            elif is_true_match and not is_pred_match:
                fn += 1  # Missed match!
            else:
                tn += 1

            comp2: AddressComponents = r2["components"]
            is_inc2 = (comp2.flat_no.value is None or comp2.pin.value is None or comp2.building.value is None)
            if is_inc1 or is_inc2:
                incomplete_total += 1
                if is_true_match == is_pred_match:
                    incomplete_correct += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    false_merge_rate = fp / (tp + fp) if (tp + fp) > 0 else 0.0
    missed_match_rate = fn / (tp + fn) if (tp + fn) > 0 else 0.0
    inc_accuracy = incomplete_correct / incomplete_total if incomplete_total > 0 else 1.0

    return {
        "has_ground_truth": True,
        "evaluated_records": n,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "false_merge_rate": round(false_merge_rate * 100, 2),
        "missed_match_rate": round(missed_match_rate * 100, 2),
        "accuracy_on_incomplete": round(inc_accuracy * 100, 2),
    }


def compute_block_histogram(block_sizes: Dict[str, int]) -> List[Dict[str, Any]]:
    """Bins block sizes for the dashboard histogram."""
    bins = [
        ("1-10", 1, 10),
        ("11-50", 11, 50),
        ("51-100", 51, 100),
        ("101-250", 101, 250),
        ("251-500", 251, 500),
        (">500 (Oversized)", 501, 1000000),
    ]
    counts = {label: 0 for label, _, _ in bins}
    for size in block_sizes.values():
        for label, low, high in bins:
            if low <= size <= high:
                counts[label] += 1
                break
    return [{"range": label, "count": counts[label], "is_oversized": (label == ">500 (Oversized)")} for label, _, _ in bins]


# =====================================================================
# REST Endpoints
# =====================================================================

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "AddressMatch", "version": "1.0.0"}


@app.get("/api/config/thresholds")
def get_thresholds():
    return state.thresholds.to_dict()


@app.post("/api/config/thresholds")
def update_thresholds(req: ThresholdConfigRequest):
    state.thresholds.threshold_auto = req.threshold_auto
    state.thresholds.threshold_review = req.threshold_review
    return {"status": "success", "thresholds": state.thresholds.to_dict()}


@app.post("/api/playground/match")
def playground_match(req: PlaygroundRequest):
    """
    Live side-by-side comparison of two addresses.
    Returns normalized forms, extracted components with confidence,
    per-component similarity breakdown, conflict flags, and policy verdict.
    """
    t_cfg = PolicyThresholds(
        threshold_auto=req.threshold_auto or state.thresholds.threshold_auto,
        threshold_review=req.threshold_review or state.thresholds.threshold_review
    )

    norm1 = normalize_address(req.address1)
    norm2 = normalize_address(req.address2)

    comp1 = extract_components(norm1)
    comp2 = extract_components(norm2)

    score_res = calculate_similarity(comp1, comp2, norm1, norm2)
    tier, tier_reason = evaluate_tier(score_res, t_cfg)

    return {
        "address1": {
            "raw": req.address1,
            "normalized": norm1,
            "components": comp1.to_dict()
        },
        "address2": {
            "raw": req.address2,
            "normalized": norm2,
            "components": comp2.to_dict()
        },
        "match_result": score_res.to_dict(),
        "tier": tier.value,
        "tier_reason": tier_reason,
        "thresholds_applied": t_cfg.to_dict()
    }


@app.get("/api/synthetic/sample")
def get_sample_addresses():
    """Returns canonical reference dataset (A101-A104)."""
    return {
        "canonical_set": REFERENCE_A101_A104,
        "description": "Exact benchmark set: A101-A104 on Lotus Apartments, JLN Road, Jaipur."
    }


@app.post("/api/batch/run")
def run_batch_pipeline(req: BatchRunRequest):
    """
    Runs the full end-to-end deduplication pipeline over synthetic or reference data.
    """
    # 1. Prepare records
    if req.source == "canonical":
        raw_dataset = REFERENCE_A101_A104
    else:
        raw_dataset = generate_synthetic_dataset(
            num_records=req.num_records,
            seed=req.seed,
            include_canonical_reference=True
        )

    # 2. Normalize and Extract
    processed_records: List[Dict[str, Any]] = []
    for item in raw_dataset:
        norm = normalize_address(item["raw_address"])
        comp = extract_components(norm)
        processed_records.append({
            "id": item["id"],
            "raw_address": item["raw_address"],
            "normalized": norm,
            "components": comp,
            "ground_truth_group": item.get("ground_truth_group")
        })

    state.current_records = {r["id"]: r for r in processed_records}

    # 3. Blocking
    engine = BlockingEngine(max_block_size=req.max_block_size)
    blocking_res = engine.generate_candidate_pairs(processed_records)

    # 4. Consistency-Checked Grouping
    clustering = run_grouping(
        records=processed_records,
        candidate_pairs=blocking_res.candidate_pairs,
        thresholds=state.thresholds
    )
    state.current_clustering = clustering
    state.review_queue = clustering.review_queue

    # 5. Representative Selection
    groups_dict: Dict[str, GroupRepresentation] = {}
    for gid, member_ids in clustering.groups.items():
        member_records = [state.current_records[mid] for mid in member_ids]
        groups_dict[gid] = select_representative(gid, member_records)
    state.current_groups = groups_dict

    # 6. Build Flattened Record Rows for Table
    table_rows: List[Dict[str, Any]] = []
    for r in processed_records:
        rid = r["id"]
        gid = clustering.record_to_group[rid]
        rep = groups_dict[gid]
        comp = r["components"]

        # Determine record-level tier
        is_rep = (rid == rep.representative_record_id)
        is_in_review = any(item.id1 == rid or item.id2 == rid for item in clustering.review_queue)
        
        if is_in_review:
            tier_label = Tier.REVIEW.value
        elif len(clustering.groups[gid]) > 1:
            tier_label = Tier.AUTO_MERGE.value
        else:
            tier_label = Tier.SEPARATE.value

        table_rows.append({
            "id": rid,
            "raw_address": r["raw_address"],
            "group_id": gid,
            "representative_id": rep.representative_record_id,
            "representative_address": rep.representative_address,
            "is_representative": is_rep,
            "tier": tier_label,
            "ground_truth_group": r.get("ground_truth_group"),
            "components": comp.to_dict()
        })

    # 7. Metrics & Block Histogram
    metrics = compute_metrics(state.current_records, clustering.record_to_group)
    state.latest_metrics = metrics

    hist = compute_block_histogram(blocking_res.block_sizes)
    state.blocking_summary = {
        "total_records": len(processed_records),
        "naive_comparisons": blocking_res.naive_comparisons,
        "candidate_comparisons": blocking_res.total_comparisons_generated,
        "reduction_ratio": blocking_res.reduction_ratio,
        "oversized_blocks_count": len(blocking_res.oversized_blocks),
        "oversized_blocks": [
            {
                "key": ob.key,
                "original_size": ob.original_size,
                "sub_block_field": ob.sub_block_field,
                "sub_blocks_created": ob.sub_blocks_created
            }
            for ob in blocking_res.oversized_blocks
        ],
        "histogram": hist
    }

    return {
        "status": "success",
        "record_count": len(table_rows),
        "group_count": len(groups_dict),
        "records": table_rows,
        "groups": [g.to_dict() for g in groups_dict.values()],
        "metrics": metrics,
        "blocking_summary": state.blocking_summary,
        "review_queue_count": len(state.review_queue)
    }


@app.post("/api/batch/upload-csv")
async def upload_csv_pipeline(file: UploadFile = File(...), max_block_size: int = Form(500)):
    """Accepts CSV file with columns (id, address) and runs the pipeline."""
    content = await file.read()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    records: List[Dict[str, Any]] = []
    
    for idx, row in enumerate(reader):
        rec_id = row.get("id") or row.get("ID") or f"REC_{idx+1:05d}"
        addr = row.get("address") or row.get("Address") or row.get("ADDRESS")
        if not addr:
            for k in row:
                if "addr" in k.lower():
                    addr = row[k]
                    break
        if not addr:
            continue
        gt = row.get("ground_truth") or row.get("ground_truth_group") or row.get("group_id")
        records.append({
            "id": rec_id,
            "raw_address": addr,
            "ground_truth_group": gt
        })

    if not records:
        raise HTTPException(status_code=400, detail="No valid address records found in CSV.")

    # Process through pipeline
    processed_records: List[Dict[str, Any]] = []
    for item in records:
        norm = normalize_address(item["raw_address"])
        comp = extract_components(norm)
        processed_records.append({
            "id": item["id"],
            "raw_address": item["raw_address"],
            "normalized": norm,
            "components": comp,
            "ground_truth_group": item.get("ground_truth_group")
        })

    state.current_records = {r["id"]: r for r in processed_records}

    engine = BlockingEngine(max_block_size=max_block_size)
    blocking_res = engine.generate_candidate_pairs(processed_records)

    clustering = run_grouping(
        records=processed_records,
        candidate_pairs=blocking_res.candidate_pairs,
        thresholds=state.thresholds
    )
    state.current_clustering = clustering
    state.review_queue = clustering.review_queue

    groups_dict: Dict[str, GroupRepresentation] = {}
    for gid, member_ids in clustering.groups.items():
        member_records = [state.current_records[mid] for mid in member_ids]
        groups_dict[gid] = select_representative(gid, member_records)
    state.current_groups = groups_dict

    table_rows: List[Dict[str, Any]] = []
    for r in processed_records:
        rid = r["id"]
        gid = clustering.record_to_group[rid]
        rep = groups_dict[gid]
        comp = r["components"]
        is_rep = (rid == rep.representative_record_id)
        is_in_review = any(item.id1 == rid or item.id2 == rid for item in clustering.review_queue)
        
        tier_label = Tier.REVIEW.value if is_in_review else (Tier.AUTO_MERGE.value if len(clustering.groups[gid]) > 1 else Tier.SEPARATE.value)

        table_rows.append({
            "id": rid,
            "raw_address": r["raw_address"],
            "group_id": gid,
            "representative_id": rep.representative_record_id,
            "representative_address": rep.representative_address,
            "is_representative": is_rep,
            "tier": tier_label,
            "ground_truth_group": r.get("ground_truth_group"),
            "components": comp.to_dict()
        })

    metrics = compute_metrics(state.current_records, clustering.record_to_group)
    state.latest_metrics = metrics
    hist = compute_block_histogram(blocking_res.block_sizes)
    state.blocking_summary = {
        "total_records": len(processed_records),
        "naive_comparisons": blocking_res.naive_comparisons,
        "candidate_comparisons": blocking_res.total_comparisons_generated,
        "reduction_ratio": blocking_res.reduction_ratio,
        "oversized_blocks_count": len(blocking_res.oversized_blocks),
        "oversized_blocks": [
            {
                "key": ob.key,
                "original_size": ob.original_size,
                "sub_block_field": ob.sub_block_field,
                "sub_blocks_created": ob.sub_blocks_created
            }
            for ob in blocking_res.oversized_blocks
        ],
        "histogram": hist
    }

    return {
        "status": "success",
        "record_count": len(table_rows),
        "group_count": len(groups_dict),
        "records": table_rows,
        "groups": [g.to_dict() for g in groups_dict.values()],
        "metrics": metrics,
        "blocking_summary": state.blocking_summary,
        "review_queue_count": len(state.review_queue)
    }


@app.get("/api/review/list")
def get_review_queue():
    """Returns pending human review items."""
    return {
        "queue_count": len(state.review_queue),
        "items": [item.to_dict() for item in state.review_queue]
    }


@app.post("/api/review/decision")
def review_decision(req: ReviewDecisionRequest):
    """
    Handles user Approve/Reject action on uncertain or transitive conflict pairs.
    Feeds decision back into grouping and updates representatives.
    """
    item_match = None
    for item in state.review_queue:
        if (item.id1 == req.id1 and item.id2 == req.id2) or (item.id1 == req.id2 and item.id2 == req.id1):
            item_match = item
            break

    if not item_match:
        raise HTTPException(status_code=404, detail="Review item not found in queue.")

    item_match.decision = req.decision

    if req.decision == "APPROVE":
        # Force merge the two groups if no hard conflict exists
        if state.current_clustering:
            g1 = state.current_clustering.record_to_group.get(req.id1)
            g2 = state.current_clustering.record_to_group.get(req.id2)
            if g1 and g2 and g1 != g2:
                # Merge members of g2 into g1
                members_to_move = state.current_clustering.groups.get(g2, [])
                state.current_clustering.groups[g1].extend(members_to_move)
                for mid in members_to_move:
                    state.current_clustering.record_to_group[mid] = g1
                if g2 in state.current_clustering.groups:
                    del state.current_clustering.groups[g2]

                # Update representative for merged group
                merged_records = [state.current_records[mid] for mid in state.current_clustering.groups[g1]]
                state.current_groups[g1] = select_representative(g1, merged_records)
                if g2 in state.current_groups:
                    del state.current_groups[g2]

    # Recompute metrics if ground truth is present
    if state.current_clustering:
        state.latest_metrics = compute_metrics(state.current_records, state.current_clustering.record_to_group)

    return {
        "status": "success",
        "decision": req.decision,
        "pair": (req.id1, req.id2),
        "updated_group_count": len(state.current_groups) if state.current_groups else 0,
        "metrics": state.latest_metrics
    }


@app.get("/api/metrics/evaluate")
def get_metrics_evaluation():
    """Returns ground-truth metrics, false-merge rates, and block-size histogram."""
    return {
        "metrics": state.latest_metrics,
        "blocking_summary": state.blocking_summary,
        "thresholds": state.thresholds.to_dict()
    }


@app.get("/api/benchmark/scalability")
def get_scalability_data():
    """Returns scalability curve data and complexity analysis."""
    series = get_scalability_series()
    return {
        "series": series,
        "analysis_markdown": SCALABILITY_ANALYSIS_TEXT
    }


# Mount production frontend build if available
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

