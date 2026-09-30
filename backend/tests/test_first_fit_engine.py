from app.services.first_fit_engine import (
    CODE_CLEARANCE,
    CODE_NO_FIT,
    allocate_first_fit,
    free_spans_from_pillars,
)

def test_free_spans_with_pillars():
    spans = free_spans_from_pillars(30.0, [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}])
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
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars)
    assert len(r.rejected) == 1
    assert r.rejected[0].vendor_name == "Huge"

def test_clearance_offsets_next_stall_start():
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 3.0, "priority": 1},
    ]
    r = allocate_first_fit(30.0, vendors, [], clearance_m=0.5)
    assert [p.start_m for p in r.placements] == [0.0, 4.5]
    # 引擎占用的净距空隙：4.0 ~ 4.5，与图上应显示的空隙米数一致
    assert r.clearance_gaps == [(4.0, 4.5)]
    assert r.free_spans == [(7.5, 30.0)]

def test_clearance_zero_allows_touching():
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 3.0, "priority": 1},
    ]
    r = allocate_first_fit(30.0, vendors, [], clearance_m=0.0)
    assert [p.start_m for p in r.placements] == [0.0, 4.0]
    assert r.clearance_gaps == []

def test_clearance_not_required_before_first_stall_in_span():
    # 每个空档的首摊贴空档起点即可，净距只约束摊与摊之间
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 9.75, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 9.5, "priority": 1},
    ]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars, clearance_m=0.5)
    assert [p.start_m for p in r.placements] == [0.0, 10.25]
    assert r.clearance_gaps == []

def test_reject_reason_clearance_is_exclusive():
    # 10m 无柱：A 占 0-6，剩 4m；B 需 0.5 净距 + 4 = 4.5 → 净距不足
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 6.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 4.0, "priority": 1},
    ]
    r = allocate_first_fit(10.0, vendors, [], clearance_m=0.5)
    assert len(r.rejected) == 1
    rej = r.rejected[0]
    assert rej.reason_code == CODE_CLEARANCE
    assert "净距不足" in rej.reason
    assert "空档总长不够" not in rej.reason

def test_reject_reason_no_fit_is_exclusive():
    vendors = [{"id": 1, "name": "Huge", "stall_width_m": 25.0, "priority": 1}]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars, clearance_m=0.5)
    assert len(r.rejected) == 1
    rej = r.rejected[0]
    assert rej.reason_code == CODE_NO_FIT
    assert "空档总长不够" in rej.reason
    assert "净距不足" not in rej.reason

def test_clearance_consumes_gap_and_freespace_reentry():
    # 净距占用空档：4 + 0.5 + 3 + 0.5 + 2 = 10，恰好放满
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 3.0, "priority": 1},
        {"id": 3, "name": "C", "stall_width_m": 2.0, "priority": 1},
    ]
    r = allocate_first_fit(10.0, vendors, [], clearance_m=0.5)
    assert [(p.start_m, p.end_m) for p in r.placements] == [(0.0, 4.0), (4.5, 7.5), (8.0, 10.0)]
    assert r.free_spans == []
    # 取走 B 后重算，空出的位置按净距规则重新可入：C 上移至 4.5-6.5，D 落 7.0-9.5
    vendors2 = [vendors[0], vendors[2], {"id": 4, "name": "D", "stall_width_m": 2.5, "priority": 2}]
    r2 = allocate_first_fit(10.0, vendors2, [], clearance_m=0.5)
    by_name = {p.vendor_name: p for p in r2.placements}
    assert (by_name["C"].start_m, by_name["C"].end_m) == (4.5, 6.5)
    assert (by_name["D"].start_m, by_name["D"].end_m) == (7.0, 9.5)
    assert r2.clearance_gaps == [(4.0, 4.5), (6.5, 7.0)]

def test_east_segment_clearance_05_shifts_or_drops():
    # 东街段：30m，灯柱 10m/20m（厚 0.5）→ 空档 [0,9.75] [10.25,19.75] [20.25,30]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}]
    vendors = [
        {"id": 1, "name": "阿强烧烤", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "林记糖水", "stall_width_m": 3.0, "priority": 1},
        {"id": 3, "name": "大碗面", "stall_width_m": 6.0, "priority": 1},
        {"id": 4, "name": "老周水果", "stall_width_m": 5.0, "priority": 2},
        {"id": 5, "name": "小美饰品", "stall_width_m": 2.5, "priority": 2},
        {"id": 6, "name": "手作皮具", "stall_width_m": 3.5, "priority": 3},
        {"id": 7, "name": "巨型舞台车", "stall_width_m": 12.0, "priority": 9},
    ]
    base = allocate_first_fit(30.0, vendors, pillars, clearance_m=0.0)
    tight = allocate_first_fit(30.0, vendors, pillars, clearance_m=0.5)
    # 净距 0.5 后：少放至少一档，或同组合起点后移
    base_starts = {p.vendor_name: p.start_m for p in base.placements}
    tight_starts = {p.vendor_name: p.start_m for p in tight.placements}
    dropped = set(base_starts) - set(tight_starts)
    shifted = [n for n, s in tight_starts.items() if n in base_starts and s > base_starts[n]]
    assert len(tight.placements) <= len(base.placements)
    assert dropped or shifted
    # 相邻两摊（同空档内）间距 ≥ 0.5，且与引擎登记的空隙一致
    for a, b in zip(tight.clearance_gaps, tight.clearance_gaps[1:]):
        assert a[1] - a[0] >= 0.5 - 1e-9 and b[0] >= a[1]
    # 放不下若出现，两类拒因可分清
    for rej in tight.rejected:
        assert rej.reason_code in (CODE_CLEARANCE, CODE_NO_FIT)
        if rej.reason_code == CODE_CLEARANCE:
            assert "净距不足" in rej.reason and "空档总长不够" not in rej.reason
        else:
            assert "空档总长不够" in rej.reason and "净距不足" not in rej.reason

def test_clearance_drops_one_stall_when_gap_tight():
    # 净距 0 时 4+3+3 恰好贴齐塞满 10m；净距 0.5 时少放一档且拒因为净距不足
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 3.0, "priority": 1},
        {"id": 3, "name": "C", "stall_width_m": 3.0, "priority": 1},
    ]
    base = allocate_first_fit(10.0, vendors, [], clearance_m=0.0)
    assert len(base.placements) == 3
    tight = allocate_first_fit(10.0, vendors, [], clearance_m=0.5)
    assert len(tight.placements) == 2
    assert tight.rejected[0].reason_code == CODE_CLEARANCE
