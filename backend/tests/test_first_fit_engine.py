from app.services.first_fit_engine import (
    REASON_CLEARANCE, REASON_GAP, allocate_first_fit, free_spans_from_pillars,
)

PILLARS_SEED = [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}]
VENDORS_SEED = [
    {"id": 1, "name": "阿强烧烤", "stall_width_m": 4.0, "priority": 1},
    {"id": 2, "name": "林记糖水", "stall_width_m": 3.0, "priority": 1},
    {"id": 3, "name": "老周水果", "stall_width_m": 5.0, "priority": 2},
    {"id": 4, "name": "小美饰品", "stall_width_m": 2.5, "priority": 2},
    {"id": 5, "name": "大碗面", "stall_width_m": 6.0, "priority": 1},
    {"id": 6, "name": "手作皮具", "stall_width_m": 3.5, "priority": 3},
    {"id": 7, "name": "巨型舞台车", "stall_width_m": 12.0, "priority": 9},
]

def test_free_spans_with_pillars():
    spans = free_spans_from_pillars(30.0, PILLARS_SEED)
    assert len(spans) == 3
    assert spans[0][0] == 0.0

def test_first_fit_no_cross_pillar():
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 12.0, "priority": 1},
    ]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars)
    assert any(p.vendor_name == "A" for p in r.placements)
    # 12m may fit in a free span after first placement depending on remainders
    assert len(r.placements) + len(r.rejected) == 2

def test_reject_oversized():
    vendors = [{"id": 1, "name": "Huge", "stall_width_m": 25.0, "priority": 1}]
    r = allocate_first_fit(30.0, vendors, PILLARS_SEED)
    assert len(r.rejected) == 1
    assert r.rejected[0].vendor_name == "Huge"
    assert r.rejected[0].reason_code == REASON_GAP

def test_clearance_zero_allows_endpoints_touch():
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 3.0, "priority": 1},
    ]
    r = allocate_first_fit(7.0, vendors, [], clearance_m=0.0)
    assert len(r.placements) == 2
    a, b = sorted(r.placements, key=lambda p: p.start_m)
    assert b.start_m == a.end_m  # 端点相接，连续塞档
    assert r.clearance_m == 0.0

def test_clearance_shifts_second_start():
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 3.0, "priority": 1},
    ]
    r = allocate_first_fit(8.0, vendors, [], clearance_m=0.5)
    a, b = sorted(r.placements, key=lambda p: p.start_m)
    assert round(b.start_m - a.end_m, 3) == 0.5  # 新摊起点至少离开净距
    assert b.start_m == 4.5

def test_clearance_consumes_gap_one_fewer_stall():
    # 唯一柱间空档恰 8m（末端挡柱 [8.0,8.2] 封死）：净距 0 可贴齐放两摊 4+4；0.5 后只能放一摊
    pillars = [{"position_m": 8.1, "thickness_m": 0.2}]
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 4.0, "priority": 1},
    ]
    flush = allocate_first_fit(8.2, vendors, pillars, clearance_m=0.0)
    assert len(flush.placements) == 2
    gapped = allocate_first_fit(8.2, vendors, pillars, clearance_m=0.5)
    assert len(gapped.placements) == 1
    assert len(gapped.rejected) == 1
    assert gapped.rejected[0].reason_code == REASON_CLEARANCE
    assert "净距" in gapped.rejected[0].reason
    assert "空档总长不够" not in gapped.rejected[0].reason

def test_gap_reason_distinct_from_clearance():
    # 8m 空档：B(4) 让掉净距刚好能塞 → 净距不足；C(9) 端点相接也塞不下 → 空档不够
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 4.0, "priority": 1},
        {"id": 3, "name": "C", "stall_width_m": 9.0, "priority": 2},
    ]
    r = allocate_first_fit(8.0, vendors, [], clearance_m=0.5)
    codes = {x.vendor_name: x.reason_code for x in r.rejected}
    assert codes["B"] == REASON_CLEARANCE
    assert codes["C"] == REASON_GAP
    # 两类拒因互斥：每条只有一个 code，且净距句不与空档句并成一句
    for x in r.rejected:
        assert x.reason_code in (REASON_CLEARANCE, REASON_GAP)
        if x.reason_code == REASON_CLEARANCE:
            assert "空档总长不够" not in x.reason
        else:
            assert "净距不足" not in x.reason

def test_smaller_stall_still_uses_remaining_gap():
    # A 后空档仍按净距规则可入：更小的 D 能带着净距进同一空档
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "D", "stall_width_m": 3.5, "priority": 1},
    ]
    r = allocate_first_fit(8.0, vendors, [], clearance_m=0.5)
    assert len(r.placements) == 2
    d = next(p for p in r.placements if p.vendor_name == "D")
    assert d.start_m == 4.5

def test_east_segment_clearance_half_scenario():
    # 东街段种子数据：净距 0 → 6 放 1 拒（巨型舞台车=空档不够），贴齐塞档
    r0 = allocate_first_fit(30.0, VENDORS_SEED, PILLARS_SEED, clearance_m=0.0)
    assert len(r0.placements) == 6
    p0 = {p.vendor_name: p for p in r0.placements}
    assert p0["林记糖水"].start_m == 4.0   # 贴齐阿强烧烤终点
    assert p0["小美饰品"].start_m == 7.0   # 贴齐林记糖水终点，塞进同一柱间空档
    assert [x.reason_code for x in r0.rejected] == [REASON_GAP]
    # 净距改 0.5：起点后移（林记糖水 4.0→4.5；小美饰品被净距挤出首空档 7.0→16.25），
    # 放置数不增；任何放不下都必须能分清是净距还是空档。
    r1 = allocate_first_fit(30.0, VENDORS_SEED, PILLARS_SEED, clearance_m=0.5)
    p1 = {p.vendor_name: p for p in r1.placements}
    assert len(r1.placements) <= 6
    assert p1["林记糖水"].start_m == 4.5
    assert p1["小美饰品"].start_m > p0["小美饰品"].start_m
    # 放不下必须能分清是净距还是空档
    rej = {x.vendor_name: x.reason_code for x in r1.rejected}
    assert rej["巨型舞台车"] == REASON_GAP  # 跨柱/总长不够，不与净距混淆
    assert set(rej.values()) <= {REASON_CLEARANCE, REASON_GAP}
