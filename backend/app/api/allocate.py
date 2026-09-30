import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AllocationRun, Pillar, Segment, Vendor
from app.services.first_fit_engine import allocate_first_fit, result_to_dict
router = APIRouter(prefix="/allocate", tags=["allocate"])

def compute_result(seg: Segment, db: Session) -> dict:
    """按街段当前登记的净距现算分配结果（不落库）。"""
    pillars = [{"position_m": p.position_m, "thickness_m": p.thickness_m}
               for p in db.scalars(select(Pillar).where(Pillar.segment_id == seg.id)).all()]
    vendors = [{"id": v.id, "name": v.name, "stall_width_m": v.stall_width_m, "priority": v.priority}
               for v in db.scalars(select(Vendor).where(Vendor.market_day_id == seg.market_day_id)).all()]
    clearance = float(seg.clearance_m or 0.0)
    result = result_to_dict(allocate_first_fit(seg.width_m, vendors, pillars, clearance_m=clearance))
    result["clearance_m"] = clearance
    result["segment"] = {"id": seg.id, "name": seg.name, "width_m": seg.width_m,
                         "clearance_m": clearance}
    result["pillars"] = pillars
    return result

def is_stale(data: dict, seg: Segment) -> bool:
    """存量结果与当前街段登记口径不一致即视为改前缓存，必须重算。"""
    stored_clearance = data.get("clearance_m")
    if stored_clearance is None or abs(float(stored_clearance) - float(seg.clearance_m or 0.0)) > 1e-9:
        return True
    stored_width = (data.get("segment") or {}).get("width_m")
    return stored_width is None or abs(float(stored_width) - float(seg.width_m)) > 1e-9

@router.post("/run")
def run_allocate(segment_id: int = 1, db: Session = Depends(get_db)):
    seg = db.get(Segment, segment_id)
    if not seg: raise HTTPException(404, "街段不存在")
    result = compute_result(seg, db)
    run = AllocationRun(segment_id=segment_id, created_at=datetime.utcnow(),
                        result_json=json.dumps(result, ensure_ascii=False))
    db.add(run); db.commit(); db.refresh(run)
    return {"id": run.id, **result}

@router.get("/latest")
def latest(segment_id: int = 1, db: Session = Depends(get_db)):
    seg = db.get(Segment, segment_id)
    if not seg: raise HTTPException(404, "街段不存在")
    run = db.scalars(select(AllocationRun).where(AllocationRun.segment_id == segment_id)
                     .order_by(AllocationRun.id.desc())).first()
    if not run:
        return run_allocate(segment_id=segment_id, db=db)
    data = json.loads(run.result_json)
    if is_stale(data, seg):
        # 净距（或宽度）已改，禁止继续吃改前缓存：按新口径重算并落库
        return run_allocate(segment_id=segment_id, db=db)
    return {"id": run.id, **data}
