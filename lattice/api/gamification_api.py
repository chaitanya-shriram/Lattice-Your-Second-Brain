from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


@router.get("/stats")
def get_stats():
    from engines.gamification import get_gamification_engine
    return get_gamification_engine().get_stats()


@router.get("/xp-log")
def get_xp_log(limit: int = Query(default=20, le=100)):
    from engines.gamification import get_gamification_engine
    return get_gamification_engine().get_xp_log(limit)


@router.get("/achievements")
def get_achievements():
    from engines.gamification import get_gamification_engine
    return get_gamification_engine().get_achievements()


@router.get("/weekly-report")
def weekly_report():
    from engines.gamification import get_gamification_engine
    return get_gamification_engine().generate_weekly_report()


class XPAwardRequest(BaseModel):
    action: str
    context: str = ""


@router.post("/award")
def award_xp(body: XPAwardRequest):
    from engines.gamification import get_gamification_engine
    return get_gamification_engine().award_xp(body.action, body.context)
