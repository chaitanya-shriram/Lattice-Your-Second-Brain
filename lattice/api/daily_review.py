from fastapi import APIRouter

router = APIRouter()


@router.post("/generate")
async def generate_review():
    """Generate today's review on demand — same engine the 21:00 scheduled job calls."""
    from engines.daily_review import get_daily_review_engine
    return await get_daily_review_engine().generate()
