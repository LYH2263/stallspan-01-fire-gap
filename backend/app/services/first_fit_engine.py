"""1D First-Fit stall placement along a street segment; stalls cannot cross pillars.

摊间消防净距（clearance_m）：同一空档内，后落摊位起点与前一摊终点之间
必须至少留出 clearance_m 米；净距本身占用空档。净距为 0 时端点可相接。
拒因互斥：净距不足（clearance）与空档总长不够（no_fit）不会并成一句。
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

# 两类互斥拒因：净距不足 vs 空档总长不够
REASON_CLEARANCE = "净距不足：需为前一摊留出 {clearance} m 摊间消防净距"
REASON_NO_FIT = "空档总长不够：无连续空档可放下且不跨越挡柱"
CODE_CLEARANCE = "clearance"
CODE_NO_FIT = "no_fit"

@dataclass
class Placement:
    vendor_id: int
    vendor_name: str
    start_m: float
    end_m: float
    width_m: float

@dataclass
class Rejected:
    vendor_id: int
    vendor_name: str
    width_m: float
    reason: str
    reason_code: str  # "clearance" | "no_fit"，两类互斥

@dataclass
class AllocResult:
    placements: list[Placement]
    rejected: list[Rejected]
    free_spans: list[tuple[float, float]]
    clearance_gaps: list[tuple[float, float]]  # 引擎实际占用的摊间净距空隙

def free_spans_from_pillars(width_m: float, pillars: list[dict]) -> list[tuple[float, float]]:
    """pillars: position_m, thickness_m — treated as blocked intervals."""
    blocked = []
    for p in pillars:
        half = p.get("thickness_m", 0.4) / 2.0
        lo = max(0.0, p["position_m"] - half)
        hi = min(width_m, p["position_m"] + half)
        if hi > lo:
            blocked.append((lo, hi))
    blocked.sort()
    merged = []
    for lo, hi in blocked:
        if not merged or lo > merged[-1][1]:
            merged.append([lo, hi])
        else:
            merged[-1][1] = max(merged[-1][1], hi)
    spans = []
    cursor = 0.0
    for lo, hi in merged:
        if lo > cursor:
            spans.append((cursor, lo))
        cursor = hi
    if cursor < width_m:
        spans.append((cursor, width_m))
    return [(round(a, 3), round(b, 3)) for a, b in spans if b - a > 1e-6]

def allocate_first_fit(width_m: float, vendors: list[dict], pillars: list[dict],
                       clearance_m: float = 0.0) -> AllocResult:
    """vendors sorted by priority ascending then id; each needs stall_width_m contiguous
    in one free span (no pillar cross). 同一空档内后落摊位起点须至少离开前一摊终点
    clearance_m 米；净距为 0 时端点可相接（与连续塞档相同）。"""
    clearance_m = max(0.0, float(clearance_m))
    spans = free_spans_from_pillars(width_m, pillars)
    # mutable remaining capacity per span: [cursor, end, occupied]
    remain = [[a, b, False] for a, b in spans]
    ordered = sorted(vendors, key=lambda v: (v.get("priority", 1), v["id"]))
    placements: list[Placement] = []
    rejected: list[Rejected] = []
    gaps: list[tuple[float, float]] = []
    for v in ordered:
        need = float(v["stall_width_m"])
        placed = False
        for span in remain:
            offset = clearance_m if span[2] else 0.0
            start = span[0] + offset
            if span[1] - start + 1e-9 >= need:
                end = start + need
                if offset > 1e-9:
                    gaps.append((round(span[0], 3), round(start, 3)))
                placements.append(Placement(v["id"], v["name"], round(start, 3), round(end, 3), need))
                span[0] = end
                span[2] = True
                placed = True
                break
        if not placed:
            rejected.append(Rejected(v["id"], v["name"], need, "", ""))
    # 互斥分类：同一批摊主在净距为 0 时能放下 → 净距不足；否则 → 空档总长不够
    if rejected and clearance_m > 0:
        shadow = allocate_first_fit(width_m, vendors, pillars, clearance_m=0.0)
        placeable = {p.vendor_id for p in shadow.placements}
    else:
        placeable = set()
    for rej in rejected:
        if rej.vendor_id in placeable:
            rej.reason = REASON_CLEARANCE.format(clearance=round(clearance_m, 3))
            rej.reason_code = CODE_CLEARANCE
        else:
            rej.reason = REASON_NO_FIT
            rej.reason_code = CODE_NO_FIT
    free = [(round(a, 3), round(b, 3)) for a, b, _ in remain if b - a > 1e-6]
    return AllocResult(placements, rejected, free, gaps)

def result_to_dict(r: AllocResult) -> dict:
    return {
        "placements": [asdict(p) for p in r.placements],
        "rejected": [asdict(x) for x in r.rejected],
        "free_spans": [{"start_m": a, "end_m": b} for a, b in r.free_spans],
        "clearance_gaps": [{"start_m": a, "end_m": b} for a, b in r.clearance_gaps],
    }
