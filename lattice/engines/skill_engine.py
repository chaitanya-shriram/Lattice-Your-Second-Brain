"""
Skills Engine: loads skill definitions from vault/_skills/*.md and executes them.
Skills are reusable prompts/workflows callable as slash commands.
"""
import yaml
from pathlib import Path
from datetime import datetime
from typing import Any

from config.settings import get_settings
from storage.database import get_db
from storage.models import SkillRegistry
from llm.router import get_llm
from utils.markdown_utils import parse_frontmatter
from utils.logger import get_logger

log = get_logger("engines.skill_engine")


class SkillEngine:
    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm()

    def load_skills(self) -> list[dict]:
        """Scan vault/_skills/ and sync to SkillRegistry table."""
        skills_path = self.settings.skills_path
        skills_path.mkdir(parents=True, exist_ok=True)
        if not list(skills_path.glob("*.md")):
            self._seed_builtin_skills(skills_path)

        skills = []
        now = datetime.utcnow().isoformat()

        with get_db() as db:
            for md_file in sorted(skills_path.glob("*.md")):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    meta, body = parse_frontmatter(content)

                    skill_name = meta.get("name", md_file.stem)
                    skill_data = {
                        "name": skill_name,
                        "description": meta.get("description", ""),
                        "trigger": meta.get("trigger", f"/{skill_name}"),
                        "category": meta.get("category", "general"),
                        "prompt_template": body.strip(),
                        "file_path": str(md_file),
                    }

                    # Upsert in SQLite
                    existing = db.query(SkillRegistry).filter(
                        SkillRegistry.name == skill_name
                    ).first()
                    if existing:
                        existing.description = skill_data["description"]
                        existing.prompt_template = skill_data["prompt_template"]
                        existing.updated_at = now
                    else:
                        reg = SkillRegistry(
                            id=f"skill-{skill_name}",
                            name=skill_name,
                            trigger=skill_data["trigger"],
                            description=skill_data["description"],
                            prompt_template=skill_data["prompt_template"],
                            category=skill_data["category"],
                            usage_count=0,
                            created_at=now,
                            updated_at=now,
                        )
                        db.add(reg)

                    skills.append(skill_data)
                except Exception as e:
                    log.warning(f"Failed to load skill {md_file.name}: {e}")

        log.info(f"Loaded {len(skills)} skills")
        return skills

    async def execute(self, skill_name: str, context: dict[str, Any] = None) -> str:
        """Execute a skill by name with given context variables."""
        context = context or {}

        with get_db() as db:
            skill = db.query(SkillRegistry).filter(
                SkillRegistry.name == skill_name
            ).first()
            if not skill:
                raise ValueError(f"Skill '{skill_name}' not found. Run load_skills() first.")
            template = skill.prompt_template
            description = skill.description
            skill.usage_count = (skill.usage_count or 0) + 1
            now = datetime.utcnow().isoformat()
            skill.updated_at = now

        # Inject session context if requested
        if "{session_context}" in template:
            from llm.context_loader import build_session_context
            context["session_context"] = build_session_context()

        # Render template (simple {var} substitution)
        try:
            prompt = template.format(**context)
        except KeyError as e:
            prompt = template  # run unformatted if vars missing

        result = await self.llm.complete(prompt, system=f"You are executing the skill: {description}")
        log.info(f"Skill '{skill_name}' executed")
        return result

    def list_skills(self) -> list[dict]:
        """Return all registered skills."""
        with get_db() as db:
            skills = db.query(SkillRegistry).order_by(SkillRegistry.name).all()
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "trigger": s.trigger,
                    "description": s.description,
                    "category": s.category,
                    "usage_count": s.usage_count or 0,
                }
                for s in skills
            ]

    def _seed_builtin_skills(self, skills_path: Path):
        """Create the default built-in skill files."""
        skills = [
            (
                "daily-review",
                {
                    "name": "daily-review",
                    "description": "Generate a structured daily review",
                    "trigger": "/review",
                    "category": "productivity",
                },
                """Conduct a daily review based on my session context.

{session_context}

Generate a structured daily review:
1. What I accomplished today (from completed tasks)
2. What's still pending
3. Key ideas or insights from today's captures
4. 3 priorities for tomorrow
5. Any patterns or contradictions to flag

Be specific and actionable. Focus on what actually happened, not generic advice.""",
            ),
            (
                "explain-concept",
                {
                    "name": "explain-concept",
                    "description": "Explain a concept from the wiki in depth",
                    "trigger": "/explain",
                    "category": "learning",
                },
                """Explain the following concept from my knowledge vault:

Concept: {concept}

Context from vault:
{context}

Provide:
1. Core definition (1-2 sentences)
2. Intuition (why does this matter?)
3. Key properties or theorems
4. Connection to other concepts
5. Common misconceptions
6. Example or application

Write for a graduate student in mathematics/CS/finance.""",
            ),
            (
                "question-brainstorm",
                {
                    "name": "question-brainstorm",
                    "description": "Generate deep follow-up questions for a topic",
                    "trigger": "/questions",
                    "category": "learning",
                },
                """Generate 10 deep, research-quality questions about:

Topic: {topic}

The questions should:
- Push beyond surface understanding
- Connect to adjacent fields
- Include both theoretical and applied angles
- Range from concrete to abstract
- Some should challenge standard assumptions

Format as numbered list. Each question should be specific enough to guide a research session.""",
            ),
            (
                "week-plan",
                {
                    "name": "week-plan",
                    "description": "Plan the upcoming week based on current tasks and goals",
                    "trigger": "/week",
                    "category": "productivity",
                },
                """Plan my upcoming week.

{session_context}

Generate a structured week plan:
1. Top 3 weekly goals (from weekly/long-term tasks)
2. Daily allocation (Mon-Fri) with specific focus blocks
3. Which someday/backlog items to pull into this week
4. Learning targets (what wiki pages to deepen)
5. Any deadlines or time-sensitive items

Be realistic about time. Prefer depth over breadth.""",
            ),
        ]

        for filename, meta, body in skills:
            path = skills_path / f"{filename}.md"
            if not path.exists():
                frontmatter = "---\n" + yaml.dump(meta, default_flow_style=False) + "---\n\n"
                path.write_text(frontmatter + body, encoding="utf-8")
                log.debug(f"Created skill: {filename}.md")


_engine: SkillEngine | None = None


def get_skill_engine() -> SkillEngine:
    global _engine
    if _engine is None:
        _engine = SkillEngine()
    return _engine
