from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.tools.compare import compare_items

router = APIRouter(tags=["compare"])


class CompareRequest(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=2, max_length=5)


@router.post("/compare")
def post_compare(payload: CompareRequest, db: Session = Depends(get_db)):
    result = compare_items(db, {"item_ids": [str(i) for i in payload.item_ids]})
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data
