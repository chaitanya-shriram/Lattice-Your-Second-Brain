"""
CRM Engine: tracks people (contacts) encountered in research and academic work.
Contacts live in SQLite + optional vault note in 07-people/.
"""
import uuid
import json
from datetime import datetime
from pathlib import Path

from storage.database import get_db
from storage.models import CRMContact
from utils.logger import get_logger

log = get_logger("engines.crm_engine")


class CRMEngine:
    def __init__(self):
        from config.settings import get_settings
        self.settings = get_settings()

    def upsert_contact(
        self,
        name: str,
        role: str = None,
        institution: str = None,
        email: str = None,
        context: str = None,
        tags: list[str] = None,
    ) -> dict:
        """Create or update a CRM contact."""
        now = datetime.utcnow().isoformat()
        slug = name.lower().replace(" ", "-")
        note_path = f"07-people/{slug}.md"

        with get_db() as db:
            existing = (
                db.query(CRMContact)
                .filter(CRMContact.name.ilike(name))
                .first()
            )

            if existing:
                if role:
                    existing.role = role
                if institution:
                    existing.institution = institution
                if email:
                    existing.email = email
                if context:
                    existing.context = (existing.context or "") + f"\n\n[{now[:10]}] {context}"
                existing.interaction_count = (existing.interaction_count or 0) + 1
                existing.last_interaction = now
                existing.updated_at = now
                contact_id = existing.id
            else:
                contact_id = str(uuid.uuid4())
                contact = CRMContact(
                    id=contact_id,
                    name=name,
                    role=role,
                    institution=institution,
                    email=email,
                    vault_note_path=note_path,
                    context=context,
                    tags=json.dumps(tags or []),
                    last_interaction=now,
                    interaction_count=1,
                    created_at=now,
                    updated_at=now,
                )
                db.add(contact)

        # Write vault note
        try:
            self._write_vault_note(name, role, institution, email, context, note_path)
        except Exception as e:
            log.warning(f"Failed to write CRM vault note: {e}")

        log.info(f"CRM contact upserted: {name}")
        return {"id": contact_id, "name": name, "vault_note": note_path}

    def list_contacts(self, search: str = None) -> list[dict]:
        """List all contacts, optionally filtered."""
        with get_db() as db:
            q = db.query(CRMContact)
            if search:
                q = q.filter(
                    (CRMContact.name.ilike(f"%{search}%")) |
                    (CRMContact.institution.ilike(f"%{search}%"))
                )
            contacts = q.order_by(CRMContact.last_interaction.desc()).all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "role": c.role,
                    "institution": c.institution,
                    "email": c.email,
                    "tags": json.loads(c.tags or "[]"),
                    "interaction_count": c.interaction_count,
                    "last_interaction": c.last_interaction,
                    "vault_note_path": c.vault_note_path,
                }
                for c in contacts
            ]

    def get_contact(self, contact_id: str) -> dict | None:
        with get_db() as db:
            c = db.query(CRMContact).filter(CRMContact.id == contact_id).first()
            if not c:
                return None
            return {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "institution": c.institution,
                "email": c.email,
                "context": c.context,
                "tags": json.loads(c.tags or "[]"),
                "interaction_count": c.interaction_count,
                "last_interaction": c.last_interaction,
                "vault_note_path": c.vault_note_path,
                "created_at": c.created_at,
            }

    def _write_vault_note(
        self,
        name: str,
        role: str,
        institution: str,
        email: str,
        context: str,
        note_path: str,
    ):
        """Write or update contact vault note in 07-people/."""
        people_dir = self.settings.vault_path / "07-people"
        people_dir.mkdir(parents=True, exist_ok=True)
        full_path = self.settings.vault_path / note_path

        if full_path.exists():
            return  # Don't overwrite existing notes

        now = datetime.utcnow().date().isoformat()
        content = f"""---
name: {name}
role: {role or ''}
institution: {institution or ''}
email: {email or ''}
created: {now}
tags: [person]
---

# {name}

## Info
- **Role**: {role or 'Unknown'}
- **Institution**: {institution or 'Unknown'}
- **Email**: {email or '—'}

## Context
{context or 'Add context about this person here.'}

## Notes

## Interactions

"""
        full_path.write_text(content, encoding="utf-8")


_engine: CRMEngine | None = None


def get_crm_engine() -> CRMEngine:
    global _engine
    if _engine is None:
        _engine = CRMEngine()
    return _engine
