"""1D First-Fit stall placement along a street segment; stalls cannot cross pillars.

相邻两摊之间必须留出街段登记的消防净距 ``clearance_m``：净距占用空档，
非空柱间空档内入位需要多付一份净距；净距为 0 时允许端点相接（连续塞档）。
放不下分两类互斥拒因：``clearance``（净距不足）与 ``gap``（空档总长不够/跨挡柱）。
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

REASON_CLEARANCE = "clearance"
REASON_GAP = "gap"

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
    reason_code: str = REASON_GAP

@dataclass
class AllocResult:
    placements: list[Placement]
    rejected: list[Rejected]
    free_spans: list[tuple[float, float]]
    clearance_m: float = 0.0

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
    """vendors sorted by priority ascending then id.

    每摊需要 stall_width_m 的连续空档且不得跨越挡柱。非空柱间空档内，新摊
    起点必须比前一摊终点至少多离开 clearance_m（净距随摊一起占用空档）；
    clearance_m 为 0 时端点相接。拒因两级判定：端点相接都放不下 → 空档不够；
    端点相接能放、留净距放不下 → 净距不足。
    """
    clearance = max(0.0, float(clearance_m))
    spans = free_spans_from_pillars(width_m, pillars)
    # [下一摊可入起点, 柱间空档终点, 该空档是否已落摊]
    remain = [[a, b, False] for a, b in spans]
    ordered = sorted(vendors, key=lambda v: (v.get("priority", 1), v["id"]))
    placements: list[Placement] = []
    rejected: list[Rejected] = []
    for v in ordered:
        need = float(v["stall_width_m"])
        placed = False
        flush_fits = False  # 端点相接（净距视为0）时是否可入某个空档
        for span in remain:
            lo, hi, used = span
            avail = hi - lo  # 已落摊的空档，lo 已退过一份净距
            if avail + 1e-9 >= need:
                start = lo
                end = start + need
                placements.append(Placement(v["id"], v["name"], round(start, 3), round(end, 3), need))
                # 净距占用空档：下一摊起点至少退到 end + clearance
                span[0] = end + clearance
                span[2] = True
                placed = True
                break
            # 按净距放不下；若空档已落摊，让掉那份净距后能端点相接塞入，则属净距不足。
            # 空档还空着时 avail 即柱间空档总长，放不下就是真不够（跨柱类并入此句）。
            if used and (avail + clearance) + 1e-9 >= need:
                flush_fits = True
        if not placed:
            if flush_fits:
                reason = f"消防净距不足：相邻两摊须留 {clearance:g} m 净距，净距占用空档后放不下"
                code = REASON_CLEARANCE
            else:
                reason = "空档总长不够：无足够长的连续空档容纳该摊且不可跨越挡柱"
                code = REASON_GAP
            rejected.append(Rejected(v["id"], v["name"], need, reason, code))
    free = [(round(a, 3), round(b, 3)) for a, b, _ in remain if b - a > 1e-6]
    return AllocResult(placements, rejected, free, round(clearance, 3))

def result_to_dict(r: AllocResult) -> dict:
    return {
        "placements": [asdict(p) for p in r.placements],
        "rejected": [asdict(x) for x in r.rejected],
        "free_spans": [{"start_m": a, "end_m": b} for a, b in r.free_spans],
        "clearance_m": r.clearance_m,
    }
