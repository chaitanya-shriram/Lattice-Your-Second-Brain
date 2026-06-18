"""
Graph builder: scans vault for [[wikilinks]] → builds VaultLink + ConceptEdge + GraphEdge tables.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime

from storage.database import get_db
from storage.models import GraphEdge, ConceptEdge, VaultLink, WikiPage
from utils.markdown_utils import extract_wikilinks
from utils.logger import get_logger

log = get_logger("engines.graph_builder")


class GraphBuilder:
    def __init__(self):
        from config.settings import get_settings
        self.settings = get_settings()

    def build_vault_links(self) -> dict:
        """Scan all vault .md files → extract [[links]] → store VaultLink records."""
        vault = self.settings.vault_path
        if not vault.exists():
            return {"error": "vault not found"}

        md_files = list(vault.rglob("*.md"))
        log.info(f"Scanning {len(md_files)} vault files for wikilinks")

        now = datetime.utcnow().isoformat()
        links_created = 0

        with get_db() as db:
            db.query(VaultLink).delete()

            for file_path in md_files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    links = extract_wikilinks(content)
                    source_str = str(file_path.relative_to(vault))

                    for link in links:
                        target = link["target"]
                        resolved = _resolve_target(target, vault)
                        # target_path NOT NULL — use raw target or resolved path
                        target_path_str = (
                            str(resolved.relative_to(vault)) if resolved else target
                        )

                        vl = VaultLink(
                            id=str(uuid.uuid4()),
                            source_path=source_str,
                            target_path=target_path_str,
                            link_raw=link.get("raw", f"[[{target}]]"),
                            link_display=link.get("display", target),
                            line_number=link.get("line", 0),
                            context_snippet=link.get("context", "")[:200],
                            created_at=now,
                            updated_at=now,
                        )
                        db.add(vl)
                        links_created += 1

                except Exception as e:
                    log.warning(f"Failed to scan {file_path.name}: {e}")

        log.info(f"Vault links built: {links_created} links")
        return {"links_created": links_created}

    def build_wiki_concept_edges(self) -> dict:
        """Build ConceptEdge records between wiki pages that link to each other."""
        now = datetime.utcnow().isoformat()
        edges_created = 0

        with get_db() as db:
            db.query(ConceptEdge).delete()
            pages = db.query(WikiPage).all()
            page_by_concept = {p.concept.lower(): p for p in pages}

            for page in pages:
                vault_path = self.settings.vault_path / page.vault_path
                if not vault_path.exists():
                    continue
                content = vault_path.read_text(encoding="utf-8", errors="replace")
                links = extract_wikilinks(content)

                for link in links:
                    target_concept = link["target"].lower()
                    target_page = page_by_concept.get(target_concept)
                    if target_page and target_page.id != page.id:
                        edge = ConceptEdge(
                            id=str(uuid.uuid4()),
                            note_a=page.vault_path,
                            note_b=target_page.vault_path,
                            shared_concepts=json.dumps([page.concept, target_page.concept]),
                            weight=1.0,
                            updated_at=now,
                        )
                        db.add(edge)
                        edges_created += 1

        log.info(f"Concept edges built: {edges_created}")
        return {"edges_created": edges_created}

    def build_graph_edges(self) -> dict:
        """Build GraphEdge records from VaultLink data."""
        now = datetime.utcnow().isoformat()
        edges = 0

        with get_db() as db:
            db.query(GraphEdge).delete()
            vault_links = db.query(VaultLink).all()

            for vl in vault_links:
                edge = GraphEdge(
                    id=str(uuid.uuid4()),
                    source_note=vl.source_path,
                    target_note=vl.target_path,
                    link_type="wikilink",
                    created_at=now,
                )
                db.add(edge)
                edges += 1

        log.info(f"Graph edges built: {edges}")
        return {"graph_edges": edges}

    def build_all(self) -> dict:
        """Full graph rebuild."""
        r1 = self.build_vault_links()
        r2 = self.build_wiki_concept_edges()
        r3 = self.build_graph_edges()
        return {**r1, **r2, **r3}

    def get_graph_data(self) -> dict:
        """Return graph data as nodes + edges for D3.js visualization."""
        with get_db() as db:
            pages = db.query(WikiPage).all()
            edges = db.query(ConceptEdge).all()

            nodes = [
                {
                    "id": p.id,
                    "label": p.concept,
                    "folder": p.folder,
                    "domain": p.domain,
                    "confidence": p.confidence,
                    "version": p.version,
                }
                for p in pages
            ]

            edge_list = []
            for e in edges:
                try:
                    concepts = json.loads(e.shared_concepts)
                except Exception:
                    concepts = []
                edge_list.append({
                    "source": e.note_a,
                    "target": e.note_b,
                    "weight": e.weight,
                    "concepts": concepts,
                })

        return {"nodes": nodes, "edges": edge_list}

    def get_neighbors(self, concept: str, hops: int = 2) -> dict:
        """BFS neighborhood expansion. Used by RAG engine for context widening."""
        with get_db() as db:
            pages = db.query(WikiPage).all()
            all_edges = db.query(ConceptEdge).all()

            page_by_path = {p.vault_path: p.concept for p in pages}
            page_by_concept = {p.concept.lower(): p.vault_path for p in pages}

            adj: dict[str, set[str]] = {}
            for e in all_edges:
                adj.setdefault(e.note_a, set()).add(e.note_b)
                adj.setdefault(e.note_b, set()).add(e.note_a)

        root_path = page_by_concept.get(concept.lower())
        if not root_path:
            return {"center": concept, "neighbors": [], "hops": hops}

        visited = {root_path}
        frontier = {root_path}
        neighbor_concepts = []

        for _ in range(hops):
            nxt = set()
            for node in frontier:
                for nb in adj.get(node, set()):
                    if nb not in visited:
                        visited.add(nb)
                        nxt.add(nb)
                        c = page_by_path.get(nb)
                        if c:
                            neighbor_concepts.append(c)
            frontier = nxt
            if not frontier:
                break

        return {
            "center": concept,
            "neighbors": neighbor_concepts,
            "hops": hops,
        }


def _resolve_target(target: str, vault: Path) -> Path | None:
    slug = target.lower().replace(" ", "-")
    for pattern in [f"**/{target}.md", f"**/{slug}.md"]:
        matches = list(vault.glob(pattern))
        if matches:
            return matches[0]
    return None


_builder: GraphBuilder | None = None


def get_graph_builder() -> GraphBuilder:
    global _builder
    if _builder is None:
        _builder = GraphBuilder()
    return _builder
