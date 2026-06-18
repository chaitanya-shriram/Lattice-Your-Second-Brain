from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    bucket = Column(String, nullable=False)       # daily|weekly|long-term|someday|recurring|waiting
    priority = Column(String, default="medium")   # low|medium|high|urgent
    status = Column(String, default="inbox")      # inbox|active|in-progress|done|dropped|deferred
    topic = Column(String)
    deadline = Column(String)
    scheduled_date = Column(String)
    scheduled_time = Column(String)
    recurrence_rule = Column(String)
    estimated_minutes = Column(Integer)
    actual_minutes = Column(Integer)
    parent_id = Column(String)
    goal_id = Column(String)
    vault_note_path = Column(String)
    source = Column(String)                       # brain-dump|desktop|file-ingest|skill
    tags = Column(Text)                           # JSON array
    domain = Column(String, default="academic")   # academic|personal|professional|mixed
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    completed_at = Column(String)
    checkins = relationship("Checkin", back_populates="task")


class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True)
    original_filename = Column(String, nullable=False)
    canonical_filename = Column(String, nullable=False)
    file_type = Column(String)                    # book|paper|notes|article|unknown
    topics = Column(Text)                         # JSON array
    authors = Column(Text)                        # JSON array
    year = Column(Integer)
    stored_path = Column(String, nullable=False)
    vault_note_path = Column(String)
    raw_path = Column(String)
    compiled = Column(Integer, default=0)
    compiled_at = Column(String)
    wiki_pages = Column(Text)                     # JSON array
    ingested_at = Column(String, nullable=False)
    last_processed = Column(String)


class BrainDump(Base):
    __tablename__ = "brain_dumps"

    id = Column(String, primary_key=True)
    raw_text = Column(Text, nullable=False)
    processed_json = Column(Text)
    items_extracted = Column(Integer)
    source = Column(String)                       # desktop|file
    created_at = Column(String, nullable=False)


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(String, primary_key=True)
    concept = Column(String, nullable=False)
    folder = Column(String, nullable=False)
    vault_path = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    source_files = Column(Text)                   # JSON array
    confidence = Column(String, default="medium")
    has_contradictions = Column(Integer, default=0)
    version = Column(Integer, default=1)
    created_at = Column(String, nullable=False)
    last_compiled = Column(String, nullable=False)


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String, primary_key=True)
    source_type = Column(String, nullable=False)  # note|wiki|task|file|question
    source_id = Column(String, nullable=False)
    chunk_index = Column(Integer, default=0)
    text_chunk = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)      # JSON float array (sqlite has no BLOB via orm easily)
    created_at = Column(String, nullable=False)


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(String, primary_key=True)
    source_note = Column(String, nullable=False)
    target_note = Column(String, nullable=False)
    link_type = Column(String, default="wikilink")  # wikilink|concept|tag
    created_at = Column(String, nullable=False)


class ConceptEdge(Base):
    __tablename__ = "concept_edges"

    id = Column(String, primary_key=True)
    note_a = Column(String, nullable=False)
    note_b = Column(String, nullable=False)
    shared_concepts = Column(Text, nullable=False)  # JSON array
    weight = Column(Float, default=1.0)
    updated_at = Column(String, nullable=False)


class VaultLink(Base):
    __tablename__ = "vault_links"

    id = Column(String, primary_key=True)
    source_path = Column(String, nullable=False)
    target_path = Column(String, nullable=False)
    link_raw = Column(String, nullable=False)
    link_display = Column(String)
    line_number = Column(Integer, nullable=False)
    context_snippet = Column(String)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_vault_links_target", "target_path"),
        Index("idx_vault_links_source", "source_path"),
    )


class CRMContact(Base):
    __tablename__ = "crm_contacts"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(String)
    institution = Column(String)
    email = Column(String)
    vault_note_path = Column(String)
    context = Column(Text)
    tags = Column(Text)                           # JSON array
    last_interaction = Column(String)
    interaction_count = Column(Integer, default=0)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class SkillRegistry(Base):
    __tablename__ = "skill_registry"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    trigger = Column(String)
    description = Column(Text)
    prompt_template = Column(Text)
    category = Column(String, default="general")
    usage_count = Column(Integer, default=0)
    file_path = Column(String)
    last_run = Column(String)
    created_at = Column(String, nullable=False)
    updated_at = Column(String)


class FolderRegistry(Base):
    __tablename__ = "folder_registry"

    id = Column(String, primary_key=True)
    path = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    parent_path = Column(String)
    description = Column(Text)
    auto_tags = Column(Text)                      # JSON array
    created_at = Column(String, nullable=False)
    approved_by_user = Column(Integer, default=0)
    item_count = Column(Integer, default=0)
    last_used = Column(String)


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    scheduled_at = Column(String, nullable=False)
    responded_at = Column(String)
    response = Column(String)                     # done|in-progress|blocked|skipped
    progress_pct = Column(Integer)
    notes = Column(Text)
    task = relationship("Task", back_populates="checkins")


class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(String, primary_key=True)
    action_type = Column(String, nullable=False)
    params_json = Column(Text, nullable=False)
    reverse_params_json = Column(Text)
    executed_at = Column(String, nullable=False)
    undone_at = Column(String)
    status = Column(String, default="done")       # done|undone|failed


class HealthReport(Base):
    __tablename__ = "health_reports"

    id = Column(String, primary_key=True)
    report_type = Column(String, nullable=False)  # broken_links|contradictions|orphaned|gaps
    items_found = Column(Integer, default=0)
    report_json = Column(Text)
    auto_fixed = Column(Integer, default=0)
    created_at = Column(String, nullable=False)


class GitCommit(Base):
    __tablename__ = "git_commits"

    id = Column(String, primary_key=True)
    commit_hash = Column(String, nullable=False)
    commit_message = Column(String, nullable=False)
    files_changed = Column(Integer, default=0)
    trigger = Column(String)
    created_at = Column(String, nullable=False)


class GamificationStats(Base):
    __tablename__ = "gamification_stats"

    id = Column(String, primary_key=True, default="singleton")
    total_xp = Column(Integer, default=0)
    current_level = Column(Integer, default=0)
    capture_streak = Column(Integer, default=0)
    study_streak = Column(Integer, default=0)
    question_streak = Column(Integer, default=0)
    task_streak = Column(Integer, default=0)
    streak_shield_available = Column(Integer, default=0)
    best_capture_streak = Column(Integer, default=0)
    best_study_streak = Column(Integer, default=0)
    best_question_streak = Column(Integer, default=0)
    best_task_streak = Column(Integer, default=0)
    total_brain_dumps = Column(Integer, default=0)
    total_items_captured = Column(Integer, default=0)
    total_tasks_created = Column(Integer, default=0)
    total_tasks_completed = Column(Integer, default=0)
    total_questions_filed = Column(Integer, default=0)
    total_questions_solved = Column(Integer, default=0)
    total_files_ingested = Column(Integer, default=0)
    total_wiki_pages_compiled = Column(Integer, default=0)
    total_journal_entries = Column(Integer, default=0)
    total_focus_minutes = Column(Integer, default=0)
    last_capture_date = Column(String)
    last_study_date = Column(String)
    last_question_date = Column(String)
    last_task_date = Column(String)
    updated_at = Column(String, nullable=False)


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(String, primary_key=True)
    badge_id = Column(String, nullable=False, unique=True)
    badge_name = Column(String, nullable=False)
    unlocked_at = Column(String, nullable=False)
    xp_awarded = Column(Integer, default=0)


class XPLog(Base):
    __tablename__ = "xp_log"

    id = Column(String, primary_key=True)
    action = Column(String, nullable=False)
    xp_earned = Column(Integer, nullable=False)
    description = Column(Text)
    earned_at = Column(String, nullable=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(String, nullable=False)
