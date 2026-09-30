import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AllocationRun, Pillar, Segment, Vendor
from app.services.first_fit_engine import allocate_first_fit, result_to_dict
router = APIRouter(prefix="/allocate", tags=["allocate"])

def _compute(seg: Segment, pillars: list[dict], vendors: list[dict]) -> dict:
    result = result_to_dict(allocate_first_fit(
        seg.width_m, vendors, pillars, clearance_m=seg.clearance_m or 0.0))
    result["segment"] = {"id": seg.id, "name": seg.name, "width_m": seg.width_m,
                         "clearance_m": seg.clearance_m or 0.0}
    result["pillars"] = pillars
    return result

@router.post("/run")
def run_allocate(segment_id: int = 1, db: Session = Depends(get_db)):
    seg = db.get(Segment, segment_id)
    if not seg: raise HTTPException(404, "街段不存在")
    pillars = [{"position_m": p.position_m, "thickness_m": p.thickness_m, "label": p.label}
               for p in db.scalars(select(Pillar).where(Pillar.segment_id == segment_id)).all()]
    vendors = [{"id": v.id, "name": v.name, "stall_width_m": v.stall_width_m, "priority": v.priority}
               for v in db.scalars(select(Vendor).where(Vendor.market_day_id == seg.market_day_id)).all()]
    # 一律按街段当前净距现算，不读任何历史结果
    result = _compute(seg, pillars, vendors)
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
    # 净距已改而缓存是改前口径：作废旧结果，按新净距现算落库
    cached = float(data.get("clearance_m", 0.0) or 0.0)
    if abs(cached - float(seg.clearance_m or 0.0)) > 1e-9:
        return run_allocate(segment_id=segment_id, db=db)
    return {"id": run.id, **data}
