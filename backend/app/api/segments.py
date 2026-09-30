from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Segment
router = APIRouter(prefix="/segments", tags=["segments"])

class SegmentPatch(BaseModel):
    clearance_m: float

def to_row(r: Segment) -> dict:
    return {"id": r.id, "market_day_id": r.market_day_id, "name": r.name,
            "width_m": r.width_m, "clearance_m": r.clearance_m}

@router.get("")
def list_segments(db: Session = Depends(get_db)):
    return [to_row(r) for r in db.scalars(select(Segment).order_by(Segment.id)).all()]

@router.patch("/{segment_id}")
def update_segment(segment_id: int, patch: SegmentPatch, db: Session = Depends(get_db)):
    seg = db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(404, "街段不存在")
    if patch.clearance_m < 0:
        raise HTTPException(422, "消防净距不能为负")
    seg.clearance_m = float(patch.clearance_m)
    db.commit()
    db.refresh(seg)
    return to_row(seg)
