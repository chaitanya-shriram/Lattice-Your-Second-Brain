from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from storage.database import get_db_dependency
from storage.models import BrainDump

router = APIRouter()


class DumpRequest(BaseModel):
    text: str
    source: str = "desktop"


@router.post("/")
async def process_dump(body: DumpRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Empty brain dump")

    from engines.brain_dump import get_brain_dump_engine
    engine = get_brain_dump_engine()
    result = await engine.process(body.text, source=body.source)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.get("/history")
async def dump_history(db: Session = Depends(get_db_dependency)):
    dumps = db.query(BrainDump).order_by(BrainDump.created_at.desc()).limit(50).all()
    return [
        {
            "id": d.id,
            "source": d.source,
            "items_extracted": d.items_extracted,
            "created_at": d.created_at,
            "preview": d.raw_text[:120] + "..." if len(d.raw_text) > 120 else d.raw_text,
        }
        for d in dumps
    ]
