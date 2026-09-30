from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Segment
router = APIRouter(prefix="/segments", tags=["segments"])

class SegmentPatch(BaseModel):
    # 相邻两摊之间的最小消防净距（米），0 表示允许端点相接
    clearance_m: float = Field(ge=0, le=1000)

def to_dict(r: Segment) -> dict:
    return {"id": r.id, "market_day_id": r.market_day_id, "name": r.name,
            "width_m": r.width_m, "clearance_m": r.clearance_m}

@router.get("")
def list_segments(db: Session = Depends(get_db)):
    return [to_dict(r) for r in db.scalars(select(Segment).order_by(Segment.id)).all()]

@router.patch("/{segment_id}")
def update_segment(segment_id: int, body: SegmentPatch, db: Session = Depends(get_db)):
    seg = db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(404, "街段不存在")
    seg.clearance_m = body.clearance_m
    db.commit()
    db.refresh(seg)
    return to_dict(seg)
