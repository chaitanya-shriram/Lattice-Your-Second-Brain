from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


@router.get("/")
def list_skills():
    from engines.skill_engine import get_skill_engine
    engine = get_skill_engine()
    return engine.list_skills()


@router.post("/reload")
def reload_skills():
    from engines.skill_engine import get_skill_engine
    engine = get_skill_engine()
    skills = engine.load_skills()
    return {"loaded": len(skills), "skills": [s["name"] for s in skills]}


class SkillExecuteRequest(BaseModel):
    skill_name: str
    context: dict = {}


@router.post("/execute")
async def execute_skill(body: SkillExecuteRequest):
    from engines.skill_engine import get_skill_engine
    engine = get_skill_engine()
    try:
        result = await engine.execute(body.skill_name, body.context)
        return {"skill": body.skill_name, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
def get_session_context():
    """Return the current session context string (for debugging/inspection)."""
    from llm.context_loader import build_session_context
    return {"context": build_session_context()}
